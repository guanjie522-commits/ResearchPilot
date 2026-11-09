from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from agent import calculator as local_calculator
from agent import search_github as local_search_github
from paper_search import search_crossref_papers
from rag.qa import MAX_TOOL_TOP_K, retrieve_paper_evidence as retrieve_pdf_evidence


PROJECT_CONTEXT_PATH = Path(__file__).with_name("researchpilot_context.md")


mcp = FastMCP(
    name="ResearchPilot MCP Server",
    instructions=(
        "提供基础乘法计算、GitHub 公共仓库搜索、"
        "Crossref 学术论文检索、已导入 PDF 的本地证据检索"
        "和项目背景 Resource。"
    ),
)


@mcp.tool(
    name="calculator",
    description="计算两个数字的乘积。遇到乘法计算时使用。",
)
def calculator(
    a: Annotated[float, "第一个数字"],
    b: Annotated[float, "第二个数字"],
) -> float:
    """计算 a × b，并返回浮点数结果。"""
    return local_calculator.func(a, b)


@mcp.tool(
    name="search_github",
    description=(
        "通过 GitHub 公共 REST API 搜索公开仓库。"
        "适用于查找 GitHub 项目、开源实现或代码示例；返回前 5 个仓库。"
    ),
)
def search_github(
    query: Annotated[str, "GitHub 仓库搜索关键词"],
) -> str:
    """搜索 GitHub 公共仓库并返回精简的仓库信息。"""
    return local_search_github.func(query)


@mcp.tool(
    name="search_papers",
    description=(
        "通过 Crossref 公共 REST API 检索真实学术论文元数据。"
        "适用于论文、文献和研究主题检索；不用于 GitHub 项目。"
        "返回标题、作者、年份、期刊、DOI、URL、摘要和来源，"
        "不提供论文全文。"
    ),
)
def search_papers(
    query: Annotated[str, "英文论文检索关键词"],
    max_results: Annotated[
        int,
        Field(ge=1, le=5, description="最多返回的论文数量"),
    ] = 5,
) -> str:
    """检索 Crossref 论文元数据，最多返回 5 条精简结果。"""
    return search_crossref_papers(query, max_results)


@mcp.tool(
    name="retrieve_paper_evidence",
    description=(
        "从 ResearchPilot 已导入的本地 PDF 论文库检索真实原文证据。"
        "只返回 Chroma 命中的 PDF 文件名、页码、chunk_id、"
        "相关度分数、分数类型和受限长度原文，不生成最终答案。"
        "适用于根据本地论文回答被引用的问题；不用于在线论文搜索。"
    ),
)
def retrieve_paper_evidence(
    query: Annotated[str, "论文内容检索问题或关键词"],
    top_k: Annotated[
        int,
        Field(ge=1, le=MAX_TOOL_TOP_K, description="最多返回的证据数量"),
    ] = 4,
) -> str:
    """检索本地 PDF 索引并返回结构化原文证据。"""
    return retrieve_pdf_evidence(query, top_k)


@mcp.resource(
    "project://researchpilot/context",
    name="researchpilot_context",
    title="ResearchPilot 项目背景",
    description="ResearchPilot 的目标、技术栈、已完成阶段和当前学习阶段。",
    mime_type="text/markdown",
)
def researchpilot_context() -> str:
    """只读返回 ResearchPilot 的本地项目背景。"""
    return PROJECT_CONTEXT_PATH.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
