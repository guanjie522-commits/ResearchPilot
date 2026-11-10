from collections import defaultdict
from statistics import mean
from typing import Any


def _metric_status(available: int, total: int) -> str:
    if available == total and total:
        return "available"
    if available:
        return "partial"
    return "unavailable"


def _aggregate_numeric_metric(
    performance: list[dict[str, Any]],
    key: str,
    *,
    zero_when_no_llm_calls: bool = False,
) -> dict[str, Any]:
    values: list[int | float] = []
    for item in performance:
        value = item.get(key)
        if value is None and zero_when_no_llm_calls and item.get(
            "llm_call_count"
        ) == 0:
            value = 0
        if value is not None:
            values.append(value)
    total = round(sum(values), 6) if values else None
    status = _metric_status(len(values), len(performance))
    return {
        "value": total if status == "available" else None,
        "available_sum": total,
        "available_runs": len(values),
        "missing_runs": len(performance) - len(values),
        "status": status,
    }


def calculate_metrics(
    runs: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_variant[run["system_variant"]].append(run)

    variant_metrics: dict[str, Any] = {}
    for variant, variant_runs in sorted(by_variant.items()):
        completed = sum(run["run_status"] == "success" for run in variant_runs)
        failed = len(variant_runs) - completed
        elapsed_values = [
            float(run["elapsed_seconds"])
            for run in variant_runs
            if run.get("elapsed_seconds") is not None
        ]
        citation_checks = [
            run["citation_validation"]
            for run in variant_runs
            if run.get("citation_validation")
            and run["citation_validation"].get("passed") is not None
        ]
        performance = [
            run.get("performance") or {} for run in variant_runs
        ]
        tool_calls = [
            call
            for run in variant_runs
            for call in (run.get("tool_calls") or [])
        ]
        tool_success_values = [
            bool(call["response_received"])
            for call in tool_calls
            if call.get("response_received") is not None
        ]
        llm_calls = _aggregate_numeric_metric(performance, "llm_call_count")
        prompt_tokens = _aggregate_numeric_metric(
            performance,
            "prompt_tokens",
            zero_when_no_llm_calls=True,
        )
        completion_tokens = _aggregate_numeric_metric(
            performance,
            "completion_tokens",
            zero_when_no_llm_calls=True,
        )
        total_tokens = _aggregate_numeric_metric(
            performance,
            "total_tokens",
            zero_when_no_llm_calls=True,
        )
        chroma_seconds = _aggregate_numeric_metric(
            performance,
            "chroma_retrieval_seconds",
        )
        variant_metrics[variant] = {
            "attempted_tasks": len(variant_runs),
            "completed_tasks": completed,
            "failed_tasks": failed,
            "average_elapsed_seconds": (
                round(mean(elapsed_values), 6) if elapsed_values else None
            ),
            "tool_call_count": sum(
                len(run.get("tool_calls") or []) for run in variant_runs
            ),
            "tool_call_success": sum(tool_success_values),
            "tool_call_failure": sum(not value for value in tool_success_values),
            "tool_call_success_recorded": len(tool_success_values),
            "tool_call_success_missing": len(tool_calls) - len(tool_success_values),
            "tool_call_success_status": (
                "not_applicable"
                if not tool_calls
                else _metric_status(len(tool_success_values), len(tool_calls))
            ),
            "llm_call_count": llm_calls["value"],
            "llm_call_count_available_sum": llm_calls["available_sum"],
            "llm_metric_runs": llm_calls["available_runs"],
            "llm_metric_missing_runs": llm_calls["missing_runs"],
            "llm_metric_status": llm_calls["status"],
            "prompt_tokens": prompt_tokens["value"],
            "prompt_tokens_available_sum": prompt_tokens["available_sum"],
            "prompt_token_metric_runs": prompt_tokens["available_runs"],
            "prompt_token_metric_missing_runs": prompt_tokens["missing_runs"],
            "prompt_token_metric_status": prompt_tokens["status"],
            "completion_tokens": completion_tokens["value"],
            "completion_tokens_available_sum": completion_tokens["available_sum"],
            "completion_token_metric_runs": completion_tokens["available_runs"],
            "completion_token_metric_missing_runs": completion_tokens["missing_runs"],
            "completion_token_metric_status": completion_tokens["status"],
            "total_tokens": total_tokens["value"],
            "total_tokens_available_sum": total_tokens["available_sum"],
            "total_token_metric_runs": total_tokens["available_runs"],
            "total_token_metric_missing_runs": total_tokens["missing_runs"],
            "total_token_metric_status": total_tokens["status"],
            "chroma_retrieval_seconds": chroma_seconds["value"],
            "chroma_retrieval_seconds_available_sum": chroma_seconds[
                "available_sum"
            ],
            "chroma_retrieval_metric_runs": chroma_seconds["available_runs"],
            "chroma_retrieval_metric_missing_runs": chroma_seconds["missing_runs"],
            "chroma_retrieval_metric_status": chroma_seconds["status"],
            "citation_checks": len(citation_checks),
            "citation_checks_passed": sum(
                bool(check.get("passed")) for check in citation_checks
            ),
            "citation_checks_failed": sum(
                not bool(check.get("passed")) for check in citation_checks
            ),
            "unknown_citation_id_count": sum(
                len(check.get("unknown_citation_ids") or [])
                for check in citation_checks
            ),
            "citation_structural_validity": (
                None
                if not citation_checks
                else (
                    sum(bool(check.get("passed")) for check in citation_checks)
                    / len(citation_checks)
                )
            ),
            "citation_structural_validity_status": (
                "not_applicable"
                if not citation_checks
                else "available"
            ),
            "tool_selection_correctness": None,
            "tool_selection_correctness_status": (
                "not_applicable"
                if not tool_calls
                else "pending_human_review"
            ),
            "pending_review_tasks": len(variant_runs),
        }

    all_tool_calls = [
        call
        for run in runs
        for call in (run.get("tool_calls") or [])
    ]
    all_tool_success_values = [
        bool(call["response_received"])
        for call in all_tool_calls
        if call.get("response_received") is not None
    ]
    all_citation_checks = [
        run["citation_validation"]
        for run in runs
        if run.get("citation_validation")
        and run["citation_validation"].get("passed") is not None
    ]
    return {
        "attempted_tasks": len(runs),
        "completed_tasks": sum(run["run_status"] == "success" for run in runs),
        "failed_tasks": sum(run["run_status"] != "success" for run in runs),
        "average_elapsed_seconds": (
            round(
                mean(
                    float(run["elapsed_seconds"])
                    for run in runs
                    if run.get("elapsed_seconds") is not None
                ),
                6,
            )
            if any(run.get("elapsed_seconds") is not None for run in runs)
            else None
        ),
        "total_tool_calls": sum(len(run.get("tool_calls") or []) for run in runs),
        "variants": variant_metrics,
        "pending_review_question_count": sum(
            item.get("verification_status") == "pending_human_review"
            for item in questions
        ),
        "answer_accuracy": None,
        "answer_accuracy_status": "pending_human_review",
        "evidence_support": None,
        "evidence_support_status": "pending_human_review",
        "tool_call_success": (
            sum(all_tool_success_values)
            if all_tool_success_values
            and len(all_tool_success_values) == len(all_tool_calls)
            else None
        ),
        "tool_call_success_available_sum": sum(all_tool_success_values),
        "tool_call_success_status": (
            "not_applicable"
            if not all_tool_calls
            else _metric_status(
                len(all_tool_success_values),
                len(all_tool_calls),
            )
        ),
        "tool_selection_correctness": None,
        "tool_selection_correctness_status": "pending_human_review",
        "citation_structural_validity": (
            sum(bool(check.get("passed")) for check in all_citation_checks)
            / len(all_citation_checks)
            if all_citation_checks
            else None
        ),
        "citation_structural_validity_status": (
            "not_applicable"
            if not all_citation_checks
            else "available"
        ),
        "premature_termination": None,
        "premature_termination_status": "pending_human_review",
        "unsupported_claim": None,
        "unsupported_claim_status": "pending_human_review",
        "incorrect_abstention": None,
        "incorrect_abstention_status": "pending_human_review",
        "task_completion": None,
        "task_completion_status": "pending_human_review",
        "scientific_quality": None,
        "scientific_quality_status": "pending_human_review",
        "scope": (
            "Automatic metrics cover completion, latency, tool-call execution "
            "metadata when present, token metadata when present, and "
            "citation-ID/source structure only. Semantic correctness and "
            "evidence support remain pending human review."
        ),
    }
