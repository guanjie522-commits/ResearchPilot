import argparse
import asyncio
import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp.client.transports import PythonStdioTransport
from langchain.mcp import MCPAdapter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import DEFAULT_TOP_K  # noqa: E402
from rag.qa import answer_question  # noqa: E402
from researchpilot_rag import (  # noqa: E402
    SERVER_PATH,
    build_research_graph,
    run_research,
)
from evaluation.metrics import calculate_metrics  # noqa: E402


MODEL = "qwen3:4b"
DATASET_PATH = ROOT / "evaluation" / "dataset.json"
RESULTS_DIR = ROOT / "evaluation" / "results"


def answer_prompt(question: str) -> list:
    return [
        SystemMessage(
            content=(
                "你是 ResearchPilot benchmark 的被测助手。"
                "回答应简洁、使用中文，区分事实与假设。"
                "如果资料不足，明确说“证据不足”，不得编造来源、DOI、页码、公式或数据。"
                "不要声称阅读了未提供的论文全文。"
            )
        ),
        HumanMessage(content=question),
    ]


def make_run_record(
    question: dict[str, Any],
    variant: str,
    elapsed: float,
    answer: str,
    *,
    cited_sources: list[dict[str, Any]] | None = None,
    retrieved_chunks: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    citation_validation: dict[str, Any] | None = None,
    error_message: str | None = None,
    run_status: str = "success",
) -> dict[str, Any]:
    return {
        "question_id": question["question_id"],
        "question": question["question"],
        "question_type": question["question_type"],
        "answerable": question["answerable"],
        "reference_answer": question["reference_answer"],
        "reference_verification_status": question["verification_status"],
        "model": MODEL,
        "system_variant": variant,
        "temperature": 0,
        "top_k": DEFAULT_TOP_K,
        "final_answer": answer,
        "elapsed_seconds": round(elapsed, 6),
        "cited_sources": cited_sources or [],
        "retrieved_chunks": retrieved_chunks or [],
        "tool_calls": tool_calls or [],
        "error_message": error_message,
        "run_status": run_status,
        "citation_validation": citation_validation,
        "review_status": "pending_human_review",
    }


async def run_baseline(question: dict[str, Any], timeout: float) -> dict[str, Any]:
    llm = ChatOllama(model=MODEL, temperature=0)
    started = time.perf_counter()
    try:
        response = await asyncio.wait_for(
            llm.ainvoke(answer_prompt(question["question"])),
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        return make_run_record(
            question,
            "baseline",
            elapsed,
            str(response.content),
            citation_validation={
                "passed": None,
                "mode": "not_applicable_no_retrieval",
            },
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        status = "timeout" if isinstance(exc, asyncio.TimeoutError) else "error"
        return make_run_record(
            question,
            "baseline",
            elapsed,
            "",
            error_message=f"{type(exc).__name__}: {exc}",
            run_status=status,
        )


async def run_direct_rag(question: dict[str, Any], timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                answer_question,
                question["question"],
                DEFAULT_TOP_K,
            ),
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        chunks = [
            {
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "chunk_id": chunk.chunk_id,
                "score": chunk.score,
                "score_type": chunk.score_type,
                "text": chunk.text[:900],
            }
            for chunk in result.chunks
        ]
        cited_sources = [
            {
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in result.chunks
        ]
        return make_run_record(
            question,
            "direct_rag",
            elapsed,
            result.answer,
            cited_sources=cited_sources,
            retrieved_chunks=chunks,
            citation_validation={
                "passed": True if chunks else result.insufficient_evidence,
                "mode": "program_appended_retrieved_sources",
                "retrieved_source_count": len(chunks),
                "unknown_citation_ids": [],
            },
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        status = "timeout" if isinstance(exc, asyncio.TimeoutError) else "error"
        return make_run_record(
            question,
            "direct_rag",
            elapsed,
            "",
            error_message=f"{type(exc).__name__}: {exc}",
            run_status=status,
        )


def evidence_to_chunk(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": item["evidence_id"],
        "source_type": item["source_type"],
        "source_file": item.get("source_file"),
        "page_number": item.get("page_number"),
        "chunk_id": item.get("chunk_id"),
        "doi": item.get("doi"),
        "retrieval_score": item.get("retrieval_score"),
        "score_type": item.get("score_type"),
        "text": item["supporting_text"][:900],
    }


async def run_researchpilot(
    question: dict[str, Any],
    graph,
    timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        state = await asyncio.wait_for(
            run_research(
                graph,
                question["question"],
                f"Benchmark C: {question['question_id']}",
            ),
            timeout=timeout,
        )
        elapsed = time.perf_counter() - started
        evidence = state.get("evidence", [])
        evidence_by_id = {item["evidence_id"]: item for item in evidence}
        validation = state.get("citation_validation") or {}
        used_ids = validation.get("used_citation_ids") or []
        cited_sources = [
            {
                "evidence_id": evidence_id,
                **{
                    key: value
                    for key, value in evidence_by_id[evidence_id].items()
                    if key
                    in {
                        "source_type",
                        "source_file",
                        "page_number",
                        "chunk_id",
                        "doi",
                    }
                },
            }
            for evidence_id in used_ids
            if evidence_id in evidence_by_id
        ]
        retrieved_chunks = [
            evidence_to_chunk(item)
            for item in evidence
            if item["source_type"] == "local_pdf"
        ]
        tool_calls = [
            {
                "step_number": result["step_number"],
                "name": call["name"],
                "args": call["args"],
                "evidence_ids": call["evidence_ids"],
            }
            for result in state.get("step_results", [])
            for call in result.get("tool_calls", [])
        ]
        return make_run_record(
            question,
            "researchpilot",
            elapsed,
            state.get("final_answer", ""),
            cited_sources=cited_sources,
            retrieved_chunks=retrieved_chunks,
            tool_calls=tool_calls,
            citation_validation={
                **validation,
                "source_matches_retrieved_evidence": (
                    not validation.get("unknown_citation_ids")
                    if validation
                    else None
                ),
            },
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        status = "timeout" if isinstance(exc, asyncio.TimeoutError) else "error"
        return make_run_record(
            question,
            "researchpilot",
            elapsed,
            "",
            error_message=(
                f"{type(exc).__name__}: {exc}\n"
                + "".join(traceback.format_exception_only(type(exc), exc))
            ),
            run_status=status,
        )


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run ResearchPilot benchmark")
    parser.add_argument(
        "--questions",
        default=",".join(
            json.loads(DATASET_PATH.read_text(encoding="utf-8"))[
                "test_configuration"
            ]["selected_smoke_test_ids"]
        ),
        help="Comma-separated question IDs",
    )
    parser.add_argument(
        "--variants",
        default="baseline,direct_rag,researchpilot",
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    question_map = {
        item["question_id"]: item for item in dataset["questions"]
    }
    question_ids = [item.strip() for item in args.questions.split(",") if item.strip()]
    selected_questions = [question_map[item] for item in question_ids]
    variants = [item.strip() for item in args.variants.split(",") if item.strip()]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result_path = RESULTS_DIR / f"benchmark_{run_id}.json"
    runs: list[dict[str, Any]] = []

    adapter = MCPAdapter(
        PythonStdioTransport(
            script_path=SERVER_PATH,
            python_cmd=sys.executable,
            cwd=SERVER_PATH.parent,
        )
    )
    async with adapter:
        tools = await adapter.list_tools()
        graph = build_research_graph(adapter.client, tools)

        for question in selected_questions:
            if "baseline" in variants:
                runs.append(await run_baseline(question, args.timeout))
            if "direct_rag" in variants:
                runs.append(await run_direct_rag(question, args.timeout))
            if "researchpilot" in variants:
                runs.append(
                    await run_researchpilot(
                        question,
                        graph,
                        args.timeout,
                    )
                )

            payload = {
                "run_id": run_id,
                "dataset_version": dataset["version"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed_pending_human_review",
                "benchmark_scope": (
                    "Single-PDF questions only; no combined GitHub/online ranking."
                ),
                "questions": question_ids,
                "variants": variants,
                "runs": runs,
                "metrics": calculate_metrics(runs, selected_questions),
            }
            write_report(result_path, payload)

    print(f"Benchmark result: {result_path}")
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
