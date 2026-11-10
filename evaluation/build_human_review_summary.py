import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.build_human_review import (  # noqa: E402
    REVIEW_IDS,
    VARIANT_ORDER,
    answer_for,
    support_sources,
)


DATASET_PATH = ROOT / "evaluation" / "dataset.json"
PILOT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "formal_benchmark_pilot_20261110.json"
)
Q09_VARIANT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "benchmark_20261110T063228Z.json"
)
OUTPUT_PATH = ROOT / "evaluation" / "human_review_summary.md"


def cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def citation_for_run(run: dict[str, Any] | None) -> str:
    if not run:
        return "unavailable"
    sources = run.get("cited_sources") or []
    if not sources:
        return "无"
    rendered = []
    for source in sources:
        if source.get("source_file"):
            rendered.append(
                f"{source['source_file']} p.{source.get('page_number')}"
            )
        elif source.get("doi"):
            rendered.append(f"DOI {source['doi']}")
    return "; ".join(rendered)


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
    question_map = {
        question["question_id"]: question
        for question in dataset["questions"]
    }
    runs_by_question: dict[str, dict[str, dict[str, Any]]] = {}
    for run in pilot["runs"]:
        runs_by_question.setdefault(run["question_id"], {})[
            run["system_variant"]
        ] = run

    lines = [
        "# ResearchPilot Benchmark 人工审核摘要",
        "",
        "数据集版本：`0.3`。以下候选参考答案和模型回答均保持 "
        "`pending_human_review`，不能视为正式 Ground Truth。",
        "",
        "审核选项：`correct` / `partially_correct` / `incorrect` / "
        "`insufficient_evidence` / `needs_source_check`。",
        "",
    ]

    for question_id in REVIEW_IDS:
        question = question_map[question_id]
        runs = runs_by_question.get(question_id, {})
        sources = support_sources(question)
        lines.extend(
            [
                f"## {question_id}",
                "",
                f"**原题：** {question['question']}",
                "",
                f"**候选答案：** {question['reference_answer']}",
                "",
                "**参考证据：**",
                "",
            ]
        )
        if sources:
            for source in sources:
                lines.extend(
                    [
                        f"- `{source['source_file']}` "
                        f"p.{source.get('page_number')}",
                        f"> {source.get('supporting_excerpt')}",
                        "",
                    ]
                )
        else:
            lines.extend(
                [
                    "- N/A：预期本地论文没有支持证据，需人工确认。",
                    "",
                ]
            )
        lines.extend(
            [
                "| 模式 | 实际回答 | 真实引用 |",
                "|---|---|---|",
            ]
        )
        for variant in VARIANT_ORDER:
            run = runs.get(variant)
            lines.append(
                f"| {variant} | {cell(answer_for(runs, variant))} | "
                f"{cell(citation_for_run(run))} |"
            )
        lines.extend(
            [
                "",
                "**参考回答审核：** [ ] correct | [ ] partially_correct | "
                "[ ] incorrect | [ ] insufficient_evidence | "
                "[ ] needs_source_check",
                "",
                "**备注：** ",
                "",
            ]
        )

    variant_dataset = question_map["q09_local_pdf"]
    variant_result = json.loads(Q09_VARIANT_PATH.read_text(encoding="utf-8"))
    variant_run = variant_result["runs"][0]
    lines.extend(
        [
            "## 附录：q09_local_pdf",
            "",
            f"**原题：** {variant_dataset['question']}",
            "",
            f"**候选答案：** {variant_dataset['reference_answer']}",
            "",
            "**参考证据：** "
            f"`{variant_dataset['source_file']}` "
            f"p.{variant_dataset['page_number']}",
            "",
            f"> {variant_dataset['supporting_excerpt']}",
            "",
            "**运行状态：** `completed_pending_human_review`",
            "",
            "**真实 Tool Call：**",
            "",
            "```json",
            json.dumps(
                variant_run["tool_calls"][0]["name"],
                ensure_ascii=False,
            ),
            json.dumps(
                variant_run["tool_calls"][0]["args"],
                ensure_ascii=False,
            ),
            "```",
            "",
            "**Deep Mode 实际回答：**",
            "",
            "```text",
            variant_run["final_answer"],
            "```",
            "",
            "**真实引用来源：**",
            "",
            citation_for_run(variant_run),
            "",
            "**参考回答审核：** [ ] correct | [ ] partially_correct | "
            "[ ] incorrect | [ ] insufficient_evidence | "
            "[ ] needs_source_check",
            "",
        ]
    )

    OUTPUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Human review summary: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
