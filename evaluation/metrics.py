from collections import defaultdict
from statistics import mean
from typing import Any


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
        llm_metric_runs = sum(
            item.get("llm_call_count") is not None for item in performance
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
            "llm_call_count": sum(
                int(item.get("llm_call_count") or 0)
                for item in performance
            ),
            "llm_metric_runs": llm_metric_runs,
            "llm_metric_missing_runs": len(variant_runs) - llm_metric_runs,
            "llm_metric_status": (
                "available"
                if llm_metric_runs == len(variant_runs)
                else "partial"
                if llm_metric_runs
                else "unavailable"
            ),
            "prompt_tokens": sum(
                int(item.get("prompt_tokens") or 0)
                for item in performance
            ),
            "completion_tokens": sum(
                int(item.get("completion_tokens") or 0)
                for item in performance
            ),
            "total_tokens": sum(
                int(item.get("total_tokens") or 0)
                for item in performance
            ),
            "chroma_retrieval_seconds": round(
                sum(
                    float(item.get("chroma_retrieval_seconds") or 0)
                    for item in performance
                ),
                6,
            ),
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
            "pending_review_tasks": len(variant_runs),
        }

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
        "unsupported_claim": None,
        "unsupported_claim_status": "pending_human_review",
        "incorrect_abstention": None,
        "incorrect_abstention_status": "pending_human_review",
        "task_completion": None,
        "task_completion_status": "pending_human_review",
        "scientific_quality": None,
        "scientific_quality_status": "pending_human_review",
        "scope": (
            "Automatic metrics cover completion, elapsed time, tool calls, "
            "citation-ID existence, and retrieved-source mapping only."
        ),
    }
