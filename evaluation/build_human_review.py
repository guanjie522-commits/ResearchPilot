import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evaluation" / "dataset.json"
PILOT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "formal_benchmark_pilot_20261110.json"
)
OUTPUT_PATH = ROOT / "evaluation" / "human_review.md"
REVIEW_IDS = ("q01", "q04", "q09", "q16", "q10")
VARIANT_ORDER = ("A_baseline", "B_direct_rag", "C_fast", "D_deep")


def support_sources(question: dict[str, Any]) -> list[dict[str, Any]]:
    if question.get("supporting_sources"):
        return question["supporting_sources"]
    if question.get("source_file"):
        return [
            {
                "source_file": question["source_file"],
                "page_number": question.get("page_number"),
                "supporting_excerpt": question.get("supporting_excerpt"),
            }
        ]
    return []


def answer_for(runs: dict[str, dict[str, Any]], variant: str) -> str:
    run = runs.get(variant)
    if not run:
        return "unavailable：没有该模式的实际运行记录。"
    return run["final_answer"]


def citations_for(runs: dict[str, dict[str, Any]]) -> str:
    lines = []
    for variant in VARIANT_ORDER:
        run = runs.get(variant)
        if not run:
            lines.append(f"- {variant}: unavailable")
            continue
        sources = run.get("cited_sources") or []
        if not sources:
            lines.append(f"- {variant}: 无")
            continue
        rendered = []
        for source in sources:
            if source.get("source_file"):
                rendered.append(
                    f"{source['source_file']} p.{source.get('page_number')}"
                )
            elif source.get("doi"):
                rendered.append(f"DOI {source['doi']}")
        lines.append(f"- {variant}: " + "; ".join(rendered))
    return "\n".join(lines)


def review_questions(question_id: str) -> list[str]:
    common = [
        "回答是否直接回答了题目？",
        "每个事实性结论是否由真实支持原文支持？",
        "是否存在答案没有覆盖、但原文明确支持的限定条件？",
    ]
    specific = {
        "q01": ["“increasing entropy”与回答中的机制描述是否一致？"],
        "q04": [
            "misfit strain、defect-dipole doping、film thickness 是否完整？",
            "术语检查通过是否可能掩盖额外的不当结论？",
        ],
        "q09": [
            "原始题干的“这个扰动模型”是否明确指向本地 PDF？",
            "Deep Mode 使用 Crossref 地球物理论文是否属于来源错误？",
        ],
        "q16": [
            "回答是否同时覆盖两篇本地论文？",
            "拒答是由真实证据不足导致，还是检索漏召回导致？",
        ],
        "q10": [
            "是否确认三篇本地 PDF 均没有 500 K 超导临界温度证据？",
            "拒答是否明确且没有引入无关科学结论？",
        ],
    }
    return [*common, *specific[question_id]]


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
        "# ResearchPilot 第一轮 Benchmark 人工审核",
        "",
        "- 数据集版本：`0.3`",
        "- 首轮实际评测题：`q01`, `q04`, `q09`, `q16`, `q10`",
        "- 原始结果：`evaluation/results/formal_benchmark_pilot_20261110.json`",
        "- 当前状态：`pending_human_review`",
        "",
        "> 候选参考答案尚未人工确认。自动术语检查或引用结构通过，"
        "都不能把状态改成 `verified`。",
        "",
        "审核选项：`correct` / `partially_correct` / `incorrect` / "
        "`insufficient_evidence` / `needs_source_check`。",
        "",
    ]

    for question_id in REVIEW_IDS:
        question = question_map[question_id]
        runs = runs_by_question.get(question_id, {})
        sources = support_sources(question)
        source_files = (
            ", ".join(
                f"`{source['source_file']}` p.{source.get('page_number')}"
                for source in sources
            )
            if sources
            else "N/A（预期证据不足）"
        )
        excerpts = (
            "\n\n".join(
                f"> {source.get('supporting_excerpt')}"
                for source in sources
            )
            if sources
            else "无预期支持摘录；审核者需确认三篇 PDF 均不支持该问题。"
        )
        lines.extend(
            [
                f"## {question_id}",
                "",
                f"1. **Question ID：** `{question_id}`",
                "",
                f"2. **原始问题：** {question['question']}",
                "",
                f"3. **候选参考答案：** {question['reference_answer']}",
                "",
                "   - 状态：`pending_human_review`",
                "",
                f"4. **支持原文：**\n\n{excerpts}",
                "",
                f"5. **PDF 文件名：** {source_files}",
                "",
                "6. **页码：** "
                + (
                    ", ".join(
                        str(source.get("page_number")) for source in sources
                    )
                    if sources
                    else "N/A"
                ),
                "",
                "7. **Baseline 回答：**\n\n```text\n"
                + answer_for(runs, "A_baseline")
                + "\n```",
                "",
                "8. **Direct RAG 回答：**\n\n```text\n"
                + answer_for(runs, "B_direct_rag")
                + "\n```",
                "",
                "9. **Fast Mode 回答：**\n\n```text\n"
                + answer_for(runs, "C_fast")
                + "\n```",
                "",
                "10. **Deep Mode 回答：**\n\n```text\n"
                + answer_for(runs, "D_deep")
                + "\n```",
                "",
                "11. **真实引用来源：**\n\n"
                + citations_for(runs),
                "",
                "12. **待审核问题：**",
                "",
                *[f"- [ ] {item}" for item in review_questions(question_id)],
                "",
                "**审核决定：**",
                "",
                "- [ ] correct",
                "- [ ] partially_correct",
                "- [ ] incorrect",
                "- [ ] insufficient_evidence",
                "- [ ] needs_source_check",
                "",
                "**审核备注：**",
                "",
                "```text",
                "",
                "```",
                "",
            ]
        )
        if question_id == "q09":
            lines.extend(
                [
                    "> 数据清洗说明：原始 q09 保留不变；明确限定本地 PDF 的"
                    "变体为 `q09_local_pdf`，当前尚未运行。",
                    "",
                ]
            )
        if question_id == "q16":
            lines.extend(
                [
                    "> q16 诊断：`entropy`, `top_k=4` 返回 0 条通过阈值的"
                    "证据；两篇目标论文的支持 Chunk 均存在于 Chroma。",
                    "",
                ]
            )

    OUTPUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Human review: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
