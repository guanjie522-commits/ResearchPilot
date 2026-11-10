import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cross_paper_qa import run_pipeline as run_cross_paper_pipeline  # noqa: E402
from paper_search import search_crossref_papers  # noqa: E402
from rag.config import DEFAULT_INDEX_MANIFEST  # noqa: E402
from researchpilot_modes import run_fast_mode  # noqa: E402


@st.cache_data(ttl=60)
def indexed_pdfs() -> tuple[str, ...]:
    if not DEFAULT_INDEX_MANIFEST.exists():
        return ()
    manifest = json.loads(
        DEFAULT_INDEX_MANIFEST.read_text(encoding="utf-8")
    )
    return tuple(sorted((manifest.get("files") or {}).keys()))


@st.cache_data(ttl=60)
def load_demo_result(kind: str) -> dict[str, Any] | list[dict[str, Any]]:
    paths = {
        "pdf": ROOT / "evaluation" / "results" / "ui_smoke_fast_20261110.json",
        "paper": ROOT / "evaluation" / "results" / "ui_crossref_smoke_20261110.json",
        "cross": ROOT / "evaluation" / "results" / "cross_paper_qa_20261110T095522Z.json",
    }
    path = paths.get(kind)
    if path is None:
        raise ValueError(f"Unsupported demo kind: {kind}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_async(coroutine):
    return asyncio.run(coroutine)


def show_metrics(result: dict[str, Any]) -> None:
    performance = result.get("performance") or {}
    columns = st.columns(3)
    columns[0].metric(
        "耗时",
        f"{float(result.get('elapsed_seconds', performance.get('total_seconds', 0))):.2f}s",
    )
    columns[1].metric(
        "LLM 调用",
        str(performance.get("llm_call_count", "unavailable")),
    )
    total_tokens = performance.get("total_tokens")
    columns[2].metric(
        "Token",
        str(total_tokens) if total_tokens is not None else "unavailable",
    )


def show_pdf_result(result: dict[str, Any]) -> None:
    if result.get("historical_demo"):
        st.info("历史演示数据：不是本次实时运行。")
    status = result.get("status", "success")
    if status == "timeout":
        st.error(f"运行超时：{result.get('error', '超过任务预算')}")
        return
    if status == "error":
        st.error(f"运行失败：{result.get('error', '未知错误')}")
        return

    st.subheader("回答")
    st.markdown(result.get("final_answer", "证据不足。"))
    show_metrics(result)

    evidence = result.get("evidence") or []
    if not evidence:
        st.warning("证据不足：没有检索到满足条件的本地 PDF 片段。")
        return

    st.subheader("实际检索来源")
    st.dataframe(
        [
            {
                "Evidence ID": item.get("evidence_id"),
                "PDF": item.get("source_file"),
                "页码": item.get("page_number"),
                "Chunk ID": item.get("chunk_id"),
                "相关度": item.get("retrieval_score"),
            }
            for item in evidence
        ],
        width="stretch",
        hide_index=True,
    )
    validation = result.get("citation_validation") or {}
    if validation.get("passed"):
        st.success("引用结构校验通过；科研结论仍需人工审核。")
    elif validation.get("insufficient_evidence_stated"):
        st.info("回答明确标记为证据不足，没有可验证的 PDF 引用。")
    else:
        st.error("引用结构校验未通过，请检查回答与 Evidence Registry。")


def parse_crossref_output(text: str) -> tuple[list[dict[str, str]], dict[str, str]]:
    if text.startswith("Crossref search failed") or text.startswith(
        "Crossref search rate limit"
    ):
        return [], {"error": text}
    returned = re.search(r"Returned papers:\s*(\d+)", text)
    request_seconds = re.search(
        r"Crossref request seconds:\s*([0-9.]+)",
        text,
    )
    papers = []
    for block in re.split(r"\n\n(?=\d+\. Title:)", text):
        title = re.search(r"^\d+\. Title:\s*(.+)$", block, re.MULTILINE)
        if not title:
            continue

        def field(name: str) -> str:
            match = re.search(
                rf"^\s*{re.escape(name)}:\s*(.*)$",
                block,
                re.MULTILINE,
            )
            return match.group(1).strip() if match else ""

        papers.append(
            {
                "title": title.group(1).strip(),
                "year": field("Publication Year"),
                "journal": field("Journal"),
                "doi": field("DOI"),
                "url": field("URL"),
                "abstract": field("Abstract"),
            }
        )
    return papers, {
        "returned": returned.group(1) if returned else str(len(papers)),
        "request_seconds": (
            request_seconds.group(1) if request_seconds else "unavailable"
        ),
    }


def pdf_qa_tab(pdfs: tuple[str, ...]) -> None:
    st.header("PDF 问答")
    st.caption("Fast Mode：Chroma 检索 → Qwen3 → Evidence Registry → 引用校验")
    if not pdfs:
        st.error("当前没有已导入 PDF。请先构建本地 Chroma 索引。")
        result = st.session_state.get("pdf_qa_result")
        if result:
            show_pdf_result(result)
        return

    with st.form("pdf_qa_form"):
        selected_pdf = st.selectbox("选择已经导入的 PDF", pdfs)
        question = st.text_area(
            "研究问题",
            placeholder="例如：这篇论文研究了哪些变量？",
        )
        submitted = st.form_submit_button("运行 PDF 问答")

    if submitted:
        if not question.strip():
            st.warning("请输入研究问题。")
        else:
            started = time.perf_counter()
            with st.spinner("正在检索本地 PDF 并调用 qwen3:4b…"):
                try:
                    result = run_async(
                        asyncio.wait_for(
                            run_fast_mode(
                                question.strip(),
                                source_file=selected_pdf,
                            ),
                            timeout=180,
                        )
                    )
                    result["status"] = "success"
                except asyncio.TimeoutError:
                    result = {
                        "status": "timeout",
                        "error": "PDF 问答超过 180 秒预算。",
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                except Exception as exc:
                    result = {
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                        "elapsed_seconds": time.perf_counter() - started,
                    }
            st.session_state["pdf_qa_result"] = result

    result = st.session_state.get("pdf_qa_result")
    if result:
        show_pdf_result(result)


def paper_search_tab() -> None:
    st.header("真实论文检索")
    st.caption(
        "Crossref metadata only：只展示真实检索元数据，不表示已阅读论文全文。"
    )
    with st.form("paper_search_form"):
        query = st.text_input(
            "英文研究关键词",
            placeholder="例如：antiferroelectric energy storage",
        )
        max_results = st.slider("返回数量", 1, 5, 5)
        submitted = st.form_submit_button("搜索 Crossref")

    if submitted:
        if not query.strip():
            st.warning("请输入英文检索关键词。")
        else:
            with st.spinner("正在请求 Crossref 公共 REST API…"):
                try:
                    text = run_async(
                        asyncio.wait_for(
                            asyncio.to_thread(
                                search_crossref_papers,
                                query.strip(),
                                max_results,
                            ),
                            timeout=30,
                        )
                    )
                    papers, meta = parse_crossref_output(text)
                    state = {
                        "status": (
                            "success" if not meta.get("error") else "error"
                        ),
                        "papers": papers,
                        **meta,
                    }
                except asyncio.TimeoutError:
                    state = {
                        "status": "timeout",
                        "error": "Crossref 请求超过 30 秒预算。",
                    }
                except Exception as exc:
                    state = {
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
            st.session_state["paper_search_result"] = state

    state = st.session_state.get("paper_search_result")
    if not state:
        return
    if state["status"] != "success":
        st.error(state.get("error", "检索失败"))
        return
    if state.get("historical_demo"):
        st.info("历史演示数据：不是本次实时运行。")
    st.caption(
        f"Crossref 返回 {state.get('returned', len(state['papers']))} 篇；"
        f"请求耗时 {state.get('request_seconds', 'unavailable')} 秒。"
    )
    if not state["papers"]:
        st.warning("Crossref 没有返回匹配论文。")
        return
    for index, paper in enumerate(state["papers"], start=1):
        with st.container(border=True):
            st.markdown(f"**{index}. {paper['title']}**")
            st.write(
                f"年份：{paper['year'] or '未提供'} ｜ "
                f"期刊：{paper['journal'] or '未提供'}"
            )
            st.write(f"DOI：{paper['doi'] or '未提供'}")
            if paper["url"]:
                st.link_button("打开论文链接", paper["url"])
            if paper["abstract"]:
                with st.expander("Crossref 摘要（如提供）"):
                    st.write(paper["abstract"])


def cross_paper_tab(pdfs: tuple[str, ...]) -> None:
    st.header("跨论文比较")
    st.warning(
        "实验性功能：最多两条查询、一次生成。不会自动运行，也不会伪造进度。"
    )
    if len(pdfs) < 2:
        st.error("跨论文比较至少需要索引中有两篇 PDF。")
        result = st.session_state.get("cross_paper_result")
        if result:
            if result.get("historical_demo"):
                st.info("历史演示数据：不是本次实时运行。")
            if result.get("status") == "completed_pending_human_review":
                st.subheader("最终比较")
                st.markdown(result.get("final_answer", ""))
                columns = st.columns(4)
                columns[0].metric(
                    "检索次数",
                    len(result.get("retrieval_runs", [])),
                )
                columns[1].metric("来源数", result.get("source_count", 0))
                columns[2].metric("LLM 调用", result.get("llm_call_count", 0))
                columns[3].metric(
                    "耗时",
                    f"{float(result.get('elapsed_seconds', 0)):.2f}s",
                )
                st.dataframe(
                    [
                        {
                            "Evidence": item["evidence_id"],
                            "PDF": item["source_file"],
                            "页码": item["page_number"],
                            "Chunk ID": item["chunk_id"],
                        }
                        for item in result.get("evidence", [])
                    ],
                    width="stretch",
                    hide_index=True,
                )
        return

    with st.form("cross_paper_form"):
        question = st.text_area(
            "比较问题",
            placeholder=(
                "例如：比较这两篇本地论文的主要设计方法和研究目标。"
            ),
        )
        selected_pdfs = st.multiselect(
            "选择相关本地论文",
            options=list(pdfs),
        )
        budget = st.number_input(
            "任务预算（秒）",
            min_value=60,
            max_value=600,
            value=420,
            step=30,
        )
        submitted = st.form_submit_button(
            "运行跨论文比较",
            disabled=False,
        )

    if submitted:
        if not question.strip():
            st.warning("请输入跨论文比较问题。")
        elif len(selected_pdfs) < 2:
            st.warning("请至少选择两篇相关本地论文。")
        else:
            started = time.perf_counter()
            with st.spinner(
                "正在分解查询、检索证据并生成比较结果；此任务可能需要数分钟…"
            ):
                try:
                    result = run_async(
                        asyncio.wait_for(
                            run_cross_paper_pipeline(
                                question.strip(),
                                float(budget),
                                selected_source_files=selected_pdfs,
                            ),
                            timeout=float(budget),
                        )
                    )
                except asyncio.TimeoutError:
                    result = {
                        "status": "timeout",
                        "error": f"跨论文比较超过 {budget} 秒预算。",
                        "elapsed_seconds": time.perf_counter() - started,
                    }
                except Exception as exc:
                    result = {
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                        "elapsed_seconds": time.perf_counter() - started,
                    }
            st.session_state["cross_paper_result"] = result

    result = st.session_state.get("cross_paper_result")
    if not result:
        return
    if result.get("historical_demo"):
        st.info("历史演示数据：不是本次实时运行。")
    if result.get("status") != "completed_pending_human_review":
        st.error(
            result.get(
                "error",
                f"跨论文任务状态：{result.get('status', 'unknown')}",
            )
        )
        st.caption(
            f"实际耗时：{float(result.get('elapsed_seconds', 0)):.2f}s"
        )
        return

    st.subheader("查询")
    st.json(result.get("queries", []))
    st.subheader("最终比较")
    st.markdown(result.get("final_answer", ""))
    columns = st.columns(4)
    columns[0].metric("检索次数", len(result.get("retrieval_runs", [])))
    columns[1].metric("来源数", result.get("source_count", 0))
    columns[2].metric("LLM 调用", result.get("llm_call_count", 0))
    columns[3].metric(
        "耗时",
        f"{float(result.get('elapsed_seconds', 0)):.2f}s",
    )
    st.caption(
        f"总 Token：{result.get('total_tokens', 0)}；"
        f"来源覆盖：{result.get('source_coverage', 'unknown')}。"
    )
    st.subheader("程序化 Evidence Registry")
    st.dataframe(
        [
            {
                "Evidence": item["evidence_id"],
                "Paper": result["source_to_paper"].get(item["source_file"]),
                "PDF": item["source_file"],
                "页码": item["page_number"],
                "Chunk ID": item["chunk_id"],
                "相关度": item.get("retrieval_score"),
            }
            for item in result.get("evidence", [])
        ],
        width="stretch",
        hide_index=True,
    )
    if result.get("evidence_ownership_validation", {}).get("passed"):
        st.success("证据归属校验通过。")
    else:
        st.error("证据归属校验失败。")
    if result.get("citation_validation", {}).get("passed"):
        st.success("最终引用结构校验通过；科研结论仍需人工审核。")
    else:
        st.error("最终引用结构校验失败。")


def main() -> None:
    st.set_page_config(
        page_title="ResearchPilot Lite",
        page_icon="RP",
        layout="wide",
    )
    st.title("ResearchPilot Lite")
    st.caption(
        "本地科研 Agent 演示：PDF 问答、Crossref 元数据检索、实验性跨论文比较"
    )
    pdfs = indexed_pdfs()
    st.caption(
        f"当前索引 PDF：{len(pdfs)} 篇。页面仅在本机运行，不包含公开分享功能。"
    )

    demo_kind = st.query_params.get("demo")
    if demo_kind:
        if demo_kind == "pdf":
            result = load_demo_result("pdf")[0]
            result["historical_demo"] = True
            st.session_state["pdf_qa_result"] = result
            pdf_qa_tab(pdfs)
        elif demo_kind == "paper":
            state = load_demo_result("paper")
            state["historical_demo"] = True
            st.session_state["paper_search_result"] = state
            paper_search_tab()
        elif demo_kind == "cross":
            result = load_demo_result("cross")
            result["historical_demo"] = True
            st.session_state["cross_paper_result"] = result
            cross_paper_tab(pdfs)
        else:
            st.error("未知演示类型。")
        return

    pdf_tab, paper_tab, cross_tab = st.tabs(
        ["PDF 问答", "真实论文检索", "跨论文比较"]
    )
    with pdf_tab:
        pdf_qa_tab(pdfs)
    with paper_tab:
        paper_search_tab()
    with cross_tab:
        cross_paper_tab(pdfs)


if __name__ == "__main__":
    main()
