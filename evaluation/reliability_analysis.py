import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

from fastmcp.client.transports import PythonStdioTransport
from langchain.mcp import MCPAdapter


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.text_matching import evaluate_q04_answer  # noqa: E402
from evaluation.metrics import calculate_metrics  # noqa: E402


DATASET_PATH = ROOT / "evaluation" / "dataset.json"
PILOT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "formal_benchmark_pilot_20261110.json"
)
ANALYSIS_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "reliability_analysis_20261110.json"
)
REVIEW_PATH = ROOT / "evaluation" / "five_question_review.md"
SERVER_PATH = ROOT / "research_mcp_server.py"
PILOT_QUESTION_IDS = ("q01", "q04", "q09", "q16", "q10")


def states_insufficient_evidence(answer: str) -> bool:
    return re.search(
        r"证据不足|insufficient evidence",
        answer,
        flags=re.IGNORECASE,
    ) is not None


def source_rows(question: dict[str, Any]) -> list[dict[str, Any]]:
    if question.get("supporting_sources"):
        return list(question["supporting_sources"])
    if question.get("source_file"):
        return [
            {
                "source_file": question["source_file"],
                "page_number": question.get("page_number"),
                "supporting_excerpt": question.get("supporting_excerpt"),
            }
        ]
    return []


def cited_sources_text(run: dict[str, Any]) -> str:
    sources = run.get("cited_sources") or []
    if not sources:
        return "无"
    parts = []
    for source in sources:
        if source.get("source_file"):
            parts.append(
                f"{source['source_file']} p.{source.get('page_number')}"
            )
        elif source.get("doi"):
            parts.append(f"DOI {source['doi']}")
        elif source.get("evidence_id"):
            parts.append(source["evidence_id"])
    return "; ".join(parts)


def tool_call_summary(run: dict[str, Any]) -> dict[str, Any]:
    calls = run.get("tool_calls") or []
    if not calls:
        return {
            "tool_call_success": "not_applicable",
            "tool_selection_correctness": "not_applicable",
            "names": [],
        }
    return {
        # Historical benchmark files do not record an explicit response flag.
        # Each of these tool calls returned observable output recorded in the
        # run, so invocation completion can be inferred, but tool-choice
        # correctness is assessed separately.
        "tool_call_success": "confirmed_from_recorded_output",
        "tool_selection_correctness": "pending_human_review",
        "names": [call.get("name") for call in calls],
    }


def automatic_result(
    question: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    citation = run.get("citation_validation") or {}
    result: dict[str, Any] = {
        "citation_structural_validity": citation.get("passed"),
        "citation_structural_validity_status": (
            "not_applicable"
            if citation.get("passed") is None
            else "available"
        ),
        "abstention_detected": states_insufficient_evidence(
            run.get("final_answer", "")
        ),
        **tool_call_summary(run),
        "answer_correctness_status": "pending_human_review",
        "evidence_support_status": "pending_human_review",
    }
    if result["names"]:
        result["expected_tool_for_pilot_task"] = "retrieve_paper_evidence"
        result["tool_selection_correctness"] = (
            "correct"
            if result["names"]
            == ["retrieve_paper_evidence"]
            else "incorrect_against_task_source"
        )
    if question["question_id"] == "q04":
        prior = run.get("automated_quality_signal") or {}
        result["q04_before_normalization"] = {
            "keyword_check_passed": prior.get("keyword_check_passed"),
            "signal": prior.get("signal"),
        }
        result["q04_after_normalization"] = evaluate_q04_answer(
            run.get("final_answer", "")
        )
    return result


async def discover_tools() -> list[dict[str, Any]]:
    adapter = MCPAdapter(
        PythonStdioTransport(
            script_path=SERVER_PATH,
            python_cmd=sys.executable,
            cwd=SERVER_PATH.parent,
        )
    )
    async with adapter:
        tools = await adapter.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in tools
        ]


def build_diagnostics(
    question_map: dict[str, dict[str, Any]],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    q09 = next(
        run
        for run in runs
        if run["question_id"] == "q09" and run["system_variant"] == "D_deep"
    )
    q09_call = q09["tool_calls"][0]
    q16 = next(
        run
        for run in runs
        if run["question_id"] == "q16" and run["system_variant"] == "D_deep"
    )
    q16_call = q16["tool_calls"][0]
    return {
        "q09": {
            "original_task": question_map["q09"]["question"],
            "expected_source": source_rows(question_map["q09"]),
            "observed_tool_call": q09_call,
            "local_pdf_evidence_ids": [
                source["evidence_id"]
                for source in q09.get("cited_sources") or []
                if source.get("source_file")
            ],
            "crossref_evidence_ids": [
                source["evidence_id"]
                for source in q09.get("cited_sources") or []
                if source.get("doi")
            ],
            "confirmed_findings": [
                "Executor step 1 selected search_papers.",
                (
                    "The selected Crossref evidence was used in the final "
                    "answer instead of local PDF evidence."
                ),
                (
                    "The tool-selection failure occurs in the Executor layer; "
                    "the Writer propagates the wrong evidence."
                ),
                (
                    "The question is ambiguous because it says '这个扰动模型' "
                    "without explicitly requesting the imported local PDFs."
                ),
            ],
            "planner_plan": "unavailable_not_persisted_in_historical_result",
            "executor_step_text": "unavailable_not_persisted_in_historical_result",
            "why_model_selected_search_papers": (
                "unavailable_no_model_rationale_was_persisted"
            ),
            "replanner_decision": (
                "unavailable_not_persisted_in_historical_result"
            ),
            "replanner_detected_error": "unknown",
            "premature_termination": "unknown",
        },
        "q16": {
            "original_task": question_map["q16"]["question"],
            "expected_sources": source_rows(question_map["q16"]),
            "observed_tool_call": q16_call,
            "confirmed_findings": [
                "Executor step 1 selected retrieve_paper_evidence.",
                "The retrieval query was reduced to the single term 'entropy'.",
                "No evidence IDs were returned.",
                (
                    "The final answer stated insufficient evidence even though "
                    "the candidate question is marked answerable with real "
                    "supporting PDF excerpts."
                ),
            ],
            "tool_selection_correctness": True,
            "retrieval_miss": True,
            "incorrect_abstention": True,
            "planner_plan": "unavailable_not_persisted_in_historical_result",
            "executor_step_text": "unavailable_not_persisted_in_historical_result",
            "replanner_decision": (
                "unavailable_not_persisted_in_historical_result"
            ),
            "replanner_checked_retrieval_gap": "unknown",
            "premature_termination": "unknown",
        },
    }


def q04_before_after(runs: list[dict[str, Any]]) -> dict[str, Any]:
    q04_runs = [run for run in runs if run["question_id"] == "q04"]
    before = []
    after = []
    for run in q04_runs:
        prior = run.get("automated_quality_signal") or {}
        before.append(
            {
                "system_variant": run["system_variant"],
                "keyword_check_passed": prior.get("keyword_check_passed"),
            }
        )
        after.append(
            {
                "system_variant": run["system_variant"],
                "passed": evaluate_q04_answer(run["final_answer"])["passed"],
            }
        )
    applicable_before = [
        item for item in before if item["keyword_check_passed"] is not None
    ]
    applicable_after = [
        item
        for item in after
        if item["system_variant"] != "A_baseline"
    ]
    return {
        "before": before,
        "after": after,
        "before_passed": sum(
            bool(item["keyword_check_passed"]) for item in applicable_before
        ),
        "before_applicable": len(applicable_before),
        "after_passed": sum(bool(item["passed"]) for item in applicable_after),
        "after_applicable": len(applicable_after),
    }


def md_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def build_review_markdown(
    questions: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> str:
    by_question: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_question.setdefault(run["question_id"], []).append(run)

    lines = [
        "# ResearchPilot 第一轮 5 题人工审核表",
        "",
        "原始问题、回答和引用均来自 "
        "`evaluation/results/formal_benchmark_pilot_20261110.json`。",
        "参考答案仍未人工审核，不能视为正式 Ground Truth。",
        "",
        "自动结果只检查术语存在、拒答措辞和引用结构；"
        "Answer Correctness 与 Evidence Support 仍需人工判断。",
        "",
    ]
    for question in questions:
        qid = question["question_id"]
        lines.extend(
            [
                f"## {qid}",
                "",
                f"**原始问题：** {question['question']}",
                "",
                f"**候选参考答案：** {question['reference_answer']}",
                "",
                f"**审核状态：** "
                f"`{question['verification_status']}`",
                "",
                "**支持原文与来源：**",
                "",
            ]
        )
        sources = source_rows(question)
        if not sources:
            lines.append("- N/A：该题为证据不足题。")
        for source in sources:
            lines.extend(
                [
                    f"- `{source['source_file']}` "
                    f"p.{source.get('page_number')}",
                    "",
                    f"> {source.get('supporting_excerpt')}",
                    "",
                ]
            )
        lines.append("")
        lines.extend(
            [
                "| Mode | 实际回答 | 引用来源 | 自动评测 | 待人工审核 |",
                "|---|---|---|---|---|",
            ]
        )
        for run in by_question[qid]:
            automatic = automatic_result(question, run)
            auto_parts = [
                (
                    "Citation structural: "
                    f"{automatic['citation_structural_validity']}"
                ),
                f"Abstention: {automatic['abstention_detected']}",
            ]
            if "q04_after_normalization" in automatic:
                q04_result = automatic["q04_after_normalization"]
                auto_parts.append(
                    "q04 normalized concept check: "
                    f"{q04_result['passed']} "
                    f"{q04_result['checks']}"
                )
            if automatic["names"]:
                auto_parts.append(
                    f"Tool: {', '.join(automatic['names'])}; "
                    "Tool selection: "
                    f"{automatic['tool_selection_correctness']}; "
                    f"Tool call success: {automatic['tool_call_success']}"
                )
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_cell(run["system_variant"]),
                        md_cell(run["final_answer"]),
                        md_cell(cited_sources_text(run)),
                        md_cell("; ".join(auto_parts)),
                        (
                            "[ ] Answer correctness "
                            "<br>[ ] Evidence support"
                        ),
                    ]
                )
                + " |"
            )
        if qid == "q09":
            lines.extend(
                [
                    "",
                    "**诊断备注：** 历史记录未保存 Plan、Executor Step 文本、"
                    "Replanner decision/reason，因此无法确认上游诱因。"
                    "已确认 Deep Executor 在 step 1 使用 `search_papers`，"
                    "且最终使用了 Crossref 证据而非本地 PDF。"
                    "题干对“这个扰动模型”的指代也不够明确。",
                ]
            )
        if qid == "q16":
            lines.extend(
                [
                    "",
                    "**诊断备注：** Deep Executor 在 step 1 正确选择 "
                    "`retrieve_paper_evidence`，但查询仅为 `entropy`，"
                    "返回 0 条证据并最终拒答。检索漏召回与错误拒答可确认；"
                    "由于历史 Plan/Replanner 信息缺失，"
                    "是否属于 premature termination 无法确认。",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    question_map = {
        question["question_id"]: question
        for question in dataset["questions"]
    }
    questions = [
        question_map[question_id] for question_id in PILOT_QUESTION_IDS
    ]
    runs = pilot["runs"]
    diagnostics = build_diagnostics(question_map, runs)
    discovery = asyncio.run(discover_tools())

    per_run = []
    for run in runs:
        question = question_map[run["question_id"]]
        per_run.append(
            {
                "question_id": run["question_id"],
                "system_variant": run["system_variant"],
                "latency_seconds": run.get("elapsed_seconds"),
                "automatic": automatic_result(question, run),
                "raw_answer_preserved": True,
            }
        )

    analysis = {
        "analysis_id": "task12e_20261110",
        "source_result": str(PILOT_PATH.relative_to(ROOT)),
        "source_result_modified": False,
        "tool_discovery": {
            "scope": "live MCP discovery during this analysis",
            "historical_model_context_available": False,
            "tools": discovery,
        },
        "historical_trace_limitations": [
            "Planner plan was not saved in the q09/q16 result records.",
            "Executor current-step text and messages were not saved.",
            "Replanner decision and reason were not saved.",
            "Token fields for q09/q16 Deep runs are unavailable, not zero.",
        ],
        "q04_before_after": q04_before_after(runs),
        "diagnostics": diagnostics,
        "runs": per_run,
        "manual_review": {
            "reviewed": 0,
            "pending": len(questions),
            "status": "pending_human_review",
        },
        "recomputed_metrics": calculate_metrics(runs, questions),
    }
    ANALYSIS_PATH.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REVIEW_PATH.write_text(
        build_review_markdown(questions, runs, diagnostics),
        encoding="utf-8",
    )
    print(f"Reliability analysis: {ANALYSIS_PATH}")
    print(f"Five-question review: {REVIEW_PATH}")
    print(json.dumps(analysis["q04_before_after"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
