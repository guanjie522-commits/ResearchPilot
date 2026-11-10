import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query_decomposition import (  # noqa: E402
    query_decomposition_messages,
    repair_query_decomposition_messages,
    validate_decomposition_plan,
)
from researchpilot_rag import query_decomposer_llm  # noqa: E402


DATASET_PATH = ROOT / "evaluation" / "dataset.json"
OUTPUT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "query_decomposition_gate_checks_20261110.json"
)
QUESTION_IDS = ("q04", "q09_local_pdf", "q16", "q10")


async def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    question_map = {
        question["question_id"]: question
        for question in dataset["questions"]
    }
    checks = []
    for question_id in QUESTION_IDS:
        question = question_map[question_id]
        result = await query_decomposer_llm.ainvoke(
            query_decomposition_messages(
                question["question"],
                ["理解问题并选择最合适的检索工具", "基于证据回答"],
                (ROOT / "researchpilot_context.md").read_text(encoding="utf-8"),
            )
        )
        eligible, queries, error = validate_decomposition_plan(
            question["question"],
            (ROOT / "researchpilot_context.md").read_text(encoding="utf-8"),
            result.eligible,
            result.queries,
        )
        raw_queries = list(result.queries)
        if error:
            repaired = await query_decomposer_llm.ainvoke(
                repair_query_decomposition_messages(
                    question["question"],
                    ["理解问题并选择最合适的检索工具", "基于证据回答"],
                    (ROOT / "researchpilot_context.md").read_text(
                        encoding="utf-8"
                    ),
                    raw_queries,
                    error,
                )
            )
            eligible, queries, error = validate_decomposition_plan(
                question["question"],
                (ROOT / "researchpilot_context.md").read_text(encoding="utf-8"),
                repaired.eligible,
                repaired.queries,
            )
            if repaired.queries:
                raw_queries = list(repaired.queries)
        checks.append(
            {
                "question_id": question_id,
                "question": question["question"],
                "raw_eligible": result.eligible,
                "raw_queries": raw_queries,
                "reason": result.reason,
                "validated_eligible": eligible,
                "validated_queries": queries,
                "validation_error": error,
            }
        )
        print(
            question_id,
            "eligible=",
            eligible,
            "queries=",
            queries,
        )

    payload = {
        "check_id": "query_decomposition_gate_20261110",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "gate-only; does not execute the full Agent",
        "checks": checks,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Gate checks: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
