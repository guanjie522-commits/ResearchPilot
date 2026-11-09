import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.profiling import PerformanceProfiler  # noqa: E402
from researchpilot_modes import run_fast_mode  # noqa: E402


DATASET_PATH = ROOT / "evaluation" / "dataset.json"
RESULTS_DIR = ROOT / "evaluation" / "results"
DEEP_PROFILE_PATH = RESULTS_DIR / "profile_A_20261109T095817Z.json"


def quality_check(question_id: str, answer: str) -> dict:
    lower = answer.lower()
    if question_id == "q04":
        checks = {
            "misfit_strain": "misfit" in lower or "mis fit" in lower,
            "defect_dipoles": "defect" in lower,
            "film_thickness": "film thickness" in lower,
            "evidence_insufficient_absent": "证据不足" not in answer,
        }
        return {
            "checks": checks,
            "status": (
                "pending_human_review"
                if all(checks.values())
                else "automated_quality_failure"
            ),
        }
    checks = {
        "states_evidence_insufficient": "证据不足" in answer,
    }
    return {
        "checks": checks,
        "status": (
            "pending_human_review"
            if all(checks.values())
            else "automated_quality_failure"
        ),
    }


async def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    questions = {
        item["question_id"]: item
        for item in dataset["questions"]
        if item["question_id"] in {"q04", "q10"}
    }
    if not DEEP_PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Comparable Deep Mode profile not found: {DEEP_PROFILE_PATH}"
        )
    deep = json.loads(DEEP_PROFILE_PATH.read_text(encoding="utf-8"))
    deep_runs = {
        profile["question_id"]: profile
        for profile in deep["profiles"]
        if profile["question_id"] in {"q04", "q10"}
    }

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fast_runs = {}
    profiler = PerformanceProfiler()
    for question_id in ["q04", "q10"]:
        result = await run_fast_mode(
            questions[question_id]["question"],
            profiler=profiler,
        )
        fast_runs[question_id] = result

    comparisons = {}
    for question_id in ["q04", "q10"]:
        fast = fast_runs[question_id]
        deep_run = deep_runs[question_id]
        fast_perf = fast["performance"]
        deep_perf = deep_run["performance"]
        comparisons[question_id] = {
            "fast": {
                "total_seconds": fast_perf["total_seconds"],
                "llm_call_count": fast_perf["llm_call_count"],
                "prompt_tokens": fast_perf["prompt_tokens"],
                "completion_tokens": fast_perf["completion_tokens"],
                "chroma_retrieval_seconds": fast_perf[
                    "chroma_retrieval_seconds"
                ],
                "tool_call_count": fast_perf["tool_call_count"],
                "cold_start": fast_perf["cold_start"],
                "final_answer": fast["final_answer"],
                "citation_validation": fast["citation_validation"],
                "quality_check": quality_check(
                    question_id,
                    fast["final_answer"],
                ),
            },
            "deep": {
                "total_seconds": deep_perf["total_seconds"],
                "llm_call_count": deep_perf["llm_call_count"],
                "prompt_tokens": deep_perf["prompt_tokens"],
                "completion_tokens": deep_perf["completion_tokens"],
                "chroma_retrieval_seconds": deep_perf[
                    "chroma_retrieval_seconds"
                ],
                "tool_call_count": deep_perf["tool_call_count"],
                "cold_start": deep_perf["cold_start"],
                "final_answer": deep_run["final_answer"],
                "citation_validation": deep_run["citation_validation"],
                "quality_check": quality_check(
                    question_id,
                    deep_run["final_answer"],
                ),
            },
            "fast_time_reduction_percent": round(
                (
                    1
                    - fast_perf["total_seconds"] / deep_perf["total_seconds"]
                )
                * 100,
                2,
            ),
            "fast_llm_call_reduction_percent": round(
                (
                    1
                    - fast_perf["llm_call_count"]
                    / deep_perf["llm_call_count"]
                )
                * 100,
                2,
            ),
        }

    payload = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "comparison_conditions": {
            "model": "qwen3:4b",
            "temperature": 0,
            "embedding_model": "qwen3-embedding:0.6b",
            "top_k": 4,
            "fast": "existing Rag retrieve + stable default qwen + program source validation",
            "deep": (
                "historical profile from profile_A_20261109T095817Z.json; "
                "q04 cold-start and q10 warm-start as in Fast run order"
            ),
            "deep_source_profile": str(DEEP_PROFILE_PATH),
        },
        "comparisons": comparisons,
        "quality_accuracy_status": "pending_human_review",
    }
    output_path = RESULTS_DIR / f"mode_comparison_{run_id}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Mode comparison: {output_path}")
    print(json.dumps(comparisons, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
