import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query_decomposition import (  # noqa: E402
    QueryDecompositionPlan,
    query_decomposition_messages,
    remove_ungrounded_domain_terms,
    repair_query_decomposition_messages,
    validate_decomposition_plan,
)
from rag.qa import retrieve  # noqa: E402
from researchpilot_rag import (  # noqa: E402
    citation_catalog,
    validate_citations,
)


MODEL = "qwen3:4b"
TOP_K = 4
MAX_QUERIES = 2
OUTPUT_DIR = ROOT / "evaluation" / "results"
CONTEXT_PATH = ROOT / "researchpilot_context.md"


class PaperClaim(BaseModel):
    paper_code: str = Field(description="程序给定的论文代码，例如 P1")
    design_approach: str
    methodological_details: str
    evidence_ids: list[str]


class ComparisonPoint(BaseModel):
    dimension: str
    summary: str
    paper_codes: list[str]
    evidence_ids: list[str]


class CrossPaperAnswer(BaseModel):
    paper_claims: list[PaperClaim]
    comparison_points: list[ComparisonPoint]
    limitations: list[str] = Field(default_factory=list)


def structured_llm(model: ChatOllama, schema):
    return model.with_structured_output(
        schema,
        method="json_schema",
        include_raw=True,
    )


def usage_from_raw(response: Any) -> dict[str, Any]:
    raw = response.get("raw") if isinstance(response, dict) else None
    usage = getattr(raw, "usage_metadata", None)
    return dict(usage) if usage else {}


def validate_claim_sources(
    answer: CrossPaperAnswer,
    evidence_by_id: dict[str, dict[str, Any]],
    source_to_paper: dict[str, str],
) -> dict[str, Any]:
    errors = []
    used_ids = set()

    def check(payload: Any, label: str) -> None:
        for evidence_id in payload.evidence_ids:
            used_ids.add(evidence_id)
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                errors.append(f"{label}: unknown evidence ID {evidence_id}")
                continue
            expected_paper = source_to_paper[evidence["source_file"]]
            if label == "paper_claim" and payload.paper_code != expected_paper:
                errors.append(
                    f"{label}: {evidence_id} belongs to {expected_paper}, "
                    f"not {payload.paper_code}"
                )
            if label == "comparison_point" and payload.paper_codes:
                if expected_paper not in payload.paper_codes:
                    errors.append(
                        f"{label}: cited {evidence_id} from {expected_paper}, "
                        "but paper_codes omitted it"
                    )

    for claim in answer.paper_claims:
        check(claim, "paper_claim")
    for point in answer.comparison_points:
        check(point, "comparison_point")
    claim_codes = [claim.paper_code for claim in answer.paper_claims]
    if len(claim_codes) != 2:
        errors.append(
            f"paper_claim: expected 2 paper claims, got {len(claim_codes)}"
        )
    if len(set(claim_codes)) != len(claim_codes):
        errors.append("paper_claim: duplicate paper_code")
    serialized = json.dumps(answer.model_dump(), ensure_ascii=False)
    if re.search(r"[\w.\-]+\.pdf", serialized, flags=re.IGNORECASE):
        errors.append("model output contained a source filename")
    return {
        "passed": not errors,
        "errors": errors,
        "used_evidence_ids": sorted(used_ids),
    }


def render_answer(
    answer: CrossPaperAnswer,
    evidence: list[dict[str, Any]],
    source_to_paper: dict[str, str],
) -> str:
    evidence_by_id = {
        item["evidence_id"]: item for item in evidence
    }
    lines = []
    for claim in answer.paper_claims:
        files = sorted(
            {
                evidence_by_id[evidence_id]["source_file"]
                for evidence_id in claim.evidence_ids
                if evidence_id in evidence_by_id
            }
        )
        citations = " ".join(
            f"[{evidence_id}]" for evidence_id in claim.evidence_ids
        )
        lines.extend(
            [
                f"### {claim.paper_code}",
                "",
                f"来源文件（程序生成）：{', '.join(files)}",
                "",
                f"设计方法：{claim.design_approach} {citations}",
                "",
                f"技术细节：{claim.methodological_details} {citations}",
                "",
            ]
        )
    if answer.comparison_points:
        lines.extend(["## 比较", ""])
        for point in answer.comparison_points:
            citations = " ".join(
                f"[{evidence_id}]" for evidence_id in point.evidence_ids
            )
            lines.append(
                f"- **{point.dimension}**：{point.summary} {citations}"
            )
        lines.append("")
    if answer.limitations:
        lines.extend(["## 限制", ""])
        lines.extend(f"- {item}" for item in answer.limitations)
        lines.append("")
    return "\n".join(lines).strip()


def is_reference_like_chunk(text: str) -> bool:
    citation_markers = re.findall(r"\[\d+\]", text)
    if len(citation_markers) >= 4:
        return True
    if re.search(r"\bReferences?\s*:", text, flags=re.IGNORECASE):
        return len(citation_markers) >= 2
    return False


def explicit_source_file(task: str) -> str | None:
    files = sorted(
        set(
            re.findall(
                r"[\w.\-]+\.pdf",
                task,
                flags=re.IGNORECASE,
            )
        )
    )
    return files[0] if len(files) == 1 else None


async def run_pipeline(
    task: str,
    timeout: float,
    selected_source_files: list[str] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    project_context = CONTEXT_PATH.read_text(encoding="utf-8")
    decomposition_llm = ChatOllama(
        model=MODEL,
        temperature=0,
        reasoning=False,
    )
    answer_llm = ChatOllama(model=MODEL, temperature=0)
    decomposition_chain = structured_llm(
        decomposition_llm,
        QueryDecompositionPlan,
    )
    answer_chain = structured_llm(answer_llm, CrossPaperAnswer)

    llm_calls = []
    decomposition_started = time.perf_counter()
    raw_plan = await decomposition_chain.ainvoke(
        query_decomposition_messages(task, ["分析跨论文任务"], project_context)
    )
    llm_calls.append(
        {
            "role": "query_decomposer",
            "elapsed_seconds": round(
                time.perf_counter() - decomposition_started,
                6,
            ),
            "usage": usage_from_raw(raw_plan),
        }
    )
    plan = raw_plan["parsed"]
    eligible, queries, validation_error = validate_decomposition_plan(
        task,
        project_context,
        plan.eligible,
        [
            remove_ungrounded_domain_terms(
                query,
                task,
                project_context,
            )
            for query in plan.queries
        ],
    )
    if not eligible and validation_error:
        repair_started = time.perf_counter()
        repaired = await decomposition_chain.ainvoke(
            repair_query_decomposition_messages(
                task,
                ["分析跨论文任务"],
                project_context,
                plan.queries,
                validation_error,
            )
        )
        llm_calls.append(
            {
                "role": "query_decomposer_repair",
                "elapsed_seconds": round(
                    time.perf_counter() - repair_started,
                    6,
                ),
                "usage": usage_from_raw(repaired),
            }
        )
        repaired_plan = repaired["parsed"]
        eligible, queries, validation_error = validate_decomposition_plan(
            task,
            project_context,
            repaired_plan.eligible,
            [
                remove_ungrounded_domain_terms(
                    query,
                    task,
                    project_context,
                )
                for query in repaired_plan.queries
            ],
        )
    if not eligible:
        raise ValueError(
            f"Task is not eligible for cross-paper decomposition: {validation_error}"
        )
    if len(queries) > MAX_QUERIES:
        raise ValueError("Query decomposition exceeded two queries.")

    retrieval_runs = []
    chunks = []
    excluded_reference_chunks = []
    seen_chunks = set()
    source_filter = (
        sorted(set(selected_source_files))
        if selected_source_files
        else (
            [source]
            if (source := explicit_source_file(task))
            else None
        )
    )
    for query in queries:
        retrieval_started = time.perf_counter()
        matches = await asyncio.to_thread(
            retrieve,
            query,
            top_k=TOP_K,
            source_files=source_filter,
        )
        retrieval_runs.append(
            {
                "query": query,
                "top_k": TOP_K,
                "source_filter_enabled": source_filter is not None,
                "source_filter": source_filter,
                "returned_chunks": len(matches),
                "sources": sorted({item.source_file for item in matches}),
                "elapsed_seconds": round(
                    time.perf_counter() - retrieval_started,
                    6,
                ),
            }
        )
        for match in matches:
            key = (match.source_file, match.chunk_id)
            if key in seen_chunks:
                continue
            seen_chunks.add(key)
            if is_reference_like_chunk(match.text):
                excluded_reference_chunks.append(
                    {
                        "source_file": match.source_file,
                        "page_number": match.page_number,
                        "chunk_id": match.chunk_id,
                        "reason": "reference_list_like",
                    }
                )
                continue
            chunks.append(match)

    source_files = sorted({chunk.source_file for chunk in chunks})
    source_to_paper = {
        source_file: f"P{index}"
        for index, source_file in enumerate(source_files, start=1)
    }
    evidence = []
    for index, chunk in enumerate(chunks, start=1):
        evidence.append(
            {
                "evidence_id": f"S{index}",
                "source_type": "local_pdf",
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "chunk_id": chunk.chunk_id,
                "retrieval_score": chunk.score,
                "score_type": chunk.score_type,
                "supporting_text": chunk.text,
            }
        )
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    if len(source_files) < 2:
        raise ValueError(
            "Cross-paper retrieval did not reach two distinct local sources."
        )

    evidence_prompt = "\n\n".join(
        (
            f"[{item['evidence_id']}] paper_code="
            f"{source_to_paper[item['source_file']]} "
            f"source_file={item['source_file']} "
            f"page={item['page_number']} chunk_id={item['chunk_id']}\n"
            f"{item['supporting_text']}"
        )
        for item in evidence
    )
    paper_codes = ", ".join(
        f"{code}={source}"
        for source, code in source_to_paper.items()
    )
    generation_started = time.perf_counter()
    generated = await answer_chain.ainvoke(
        [
            SystemMessage(
                "你是跨论文证据综合器。只能使用给定 Evidence。"
                "paper_code 与 source_file 的映射由程序固定，不得改变。"
                "每个 paper_claim 只能引用同一 paper_code 下的 Evidence ID。"
                "每条事实必须附真实 [S#]。不得写来源文件名、DOI 或页码，"
                "不得声称阅读全文，不得用外部知识补全。"
                "如果某个目标论文没有足够证据，明确指出证据不足。"
                "所有科学结论仍等待人工审核。"
            ),
            HumanMessage(
                f"原始任务：{task}\n\n"
                f"固定论文代码：{paper_codes}\n\n"
                f"Evidence：\n{evidence_prompt}"
            ),
        ]
    )
    llm_calls.append(
        {
            "role": "final_generator",
            "elapsed_seconds": round(
                time.perf_counter() - generation_started,
                6,
            ),
            "usage": usage_from_raw(generated),
        }
    )
    answer = generated["parsed"]
    ownership = validate_claim_sources(
        answer,
        evidence_by_id,
        source_to_paper,
    )
    if not ownership["passed"]:
        raise ValueError(
            "Model output violated evidence ownership: "
            + "; ".join(ownership["errors"])
        )

    draft = render_answer(answer, evidence, source_to_paper)
    citation_validation = validate_citations(draft, evidence)
    if not citation_validation["passed"]:
        raise ValueError(
            "Final citation validation failed: "
            + json.dumps(citation_validation, ensure_ascii=False)
        )
    final_answer = draft + citation_catalog(draft, evidence)
    elapsed = time.perf_counter() - started
    token_total = sum(
        int(call["usage"].get("total_tokens") or 0)
        for call in llm_calls
    )
    return {
        "status": "completed_pending_human_review",
        "task": task,
        "queries": queries,
        "retrieval_runs": retrieval_runs,
        "excluded_reference_chunks": excluded_reference_chunks,
        "evidence": evidence,
        "source_to_paper": source_to_paper,
        "source_count": len(source_files),
        "source_coverage": (
            "2+" if len(source_files) >= 2 else "insufficient"
        ),
        "paper_claims": answer.model_dump(),
        "evidence_ownership_validation": ownership,
        "citation_validation": citation_validation,
        "final_answer": final_answer,
        "llm_calls": llm_calls,
        "llm_call_count": len(llm_calls),
        "total_tokens": token_total,
        "elapsed_seconds": round(elapsed, 6),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lightweight cross-paper QA experiment"
    )
    parser.add_argument("--question", required=True)
    parser.add_argument("--timeout", type=float, default=360.0)
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"cross_paper_qa_{run_id}.json"
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            run_pipeline(args.question, args.timeout),
            timeout=args.timeout,
        )
    except Exception as exc:
        result = {
            "status": (
                "timeout" if isinstance(exc, asyncio.TimeoutError) else "error"
            ),
            "task": args.question,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.perf_counter() - started, 6),
        }
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Cross-paper QA result: {output_path}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
