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
        "scientific_quality": None,
        "scientific_quality_status": "pending_human_review",
        "scope": (
            "Automatic metrics cover completion, elapsed time, tool calls, "
            "citation-ID existence, and retrieved-source mapping only."
        ),
    }
