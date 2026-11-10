import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field


MAX_DECOMPOSITION_QUERIES = 2
QUERY_DECOMPOSITION_PROMPT = (
    "你是 Query Decomposition Gate。只判断任务是否需要跨论文或多来源综合，"
    "并生成至多两条检索查询。"
    "只有明确要求比较、综合两个或更多不同论文/来源时才 eligible=true；"
    "“直接比较两篇不同论文”也属于 eligible=true，不能因为只比较两篇"
    "而判为简单单篇问答。"
    "简单单篇问答、单篇机制题和证据不足题均为 false。"
    "eligible=true 时必须输出两条不同、完整、可独立检索的英文子查询，"
    "每条至少 8 个英文单词并以问号结尾，保留原始研究子目标，"
    "不得只输出一个宽泛单词，"
    "不得只重复论文标签或文件名，必须包含要检索的研究方面，"
    "不得引入原题未出现的学科、对象或应用场景，"
    "不得把 PZO、entropy 等技术词替换成信息论、磁学、地质或其他领域概念，"
    "不得写答案事实，不得编造文件名。"
)
_EXPLICIT_CROSS_SOURCE_CUE = re.compile(
    r"\b(compare|comparison|contrast|synthesi[sz]e|across|complement)\b"
    r"|比较|对比|综合|跨论文|跨来源|相互补充",
    flags=re.IGNORECASE,
)
_UNGROUNDED_DOMAIN_TERMS = {
    "data",
    "information",
    "iron",
    "magnetic",
    "geology",
    "geophysics",
    "seismic",
    "telecommunication",
}
_GENERIC_QUERY_TERMS = {
    "a",
    "according",
    "and",
    "antiferroelectric",
    "application",
    "applications",
    "approach",
    "approaches",
    "are",
    "as",
    "associated",
    "based",
    "be",
    "by",
    "compare",
    "described",
    "describes",
    "design",
    "device",
    "efficiency",
    "employed",
    "detailed",
    "do",
    "does",
    "for",
    "from",
    "energy",
    "enhancing",
    "ferroelectric",
    "how",
    "identify",
    "improve",
    "improves",
    "improving",
    "in",
    "into",
    "is",
    "key",
    "main",
    "materials",
    "method",
    "methodologies",
    "methodology",
    "methods",
    "of",
    "on",
    "optimization",
    "optimizing",
    "or",
    "paper",
    "papers",
    "performance",
    "phase",
    "primary",
    "proposed",
    "propose",
    "proposes",
    "research",
    "researching",
    "study",
    "specific",
    "storage",
    "structural",
    "simulation",
    "simulations",
    "systems",
    "technique",
    "techniques",
    "the",
    "their",
    "to",
    "use",
    "used",
    "uses",
    "using",
    "what",
    "which",
    "with",
    "increase",
    "increasing",
    "field",
}


class QueryDecompositionPlan(BaseModel):
    eligible: bool = Field(
        description=(
            "是否明确要求跨论文或多来源综合，而不是简单单篇论文问答"
        )
    )
    reason: str = Field(description="分类依据，不得包含答案事实")
    queries: list[str] = Field(
        default_factory=list,
        max_length=MAX_DECOMPOSITION_QUERIES,
        description=(
            "eligible=true 时提供两条面向不同来源子目标的完整英文检索查询"
        ),
    )


def query_decomposition_messages(
    original_task: str,
    plan: list[str],
    project_context: str,
) -> list:
    return [
        SystemMessage(content=QUERY_DECOMPOSITION_PROMPT),
        HumanMessage(
            content=(
                f"原始任务：{original_task}\n\n"
                f"初始计划：\n{chr(10).join(plan)}\n\n"
                f"项目本地论文背景：\n{project_context}"
            )
        ),
    ]


def repair_query_decomposition_messages(
    original_task: str,
    plan: list[str],
    project_context: str,
    previous_queries: list[str],
    validation_error: str,
) -> list:
    return [
        SystemMessage(content=QUERY_DECOMPOSITION_PROMPT),
        HumanMessage(
            content=(
                f"原始任务：{original_task}\n\n"
                f"初始计划：\n{chr(10).join(plan)}\n\n"
                f"项目本地论文背景：\n{project_context}\n\n"
                f"上一版查询：{previous_queries}\n"
                f"校验错误：{validation_error}\n\n"
                "请保持 eligible=true，并重写恰好两条完整英文检索问句。"
                "每句至少 8 个英文单词并以问号结尾，必须明确指出"
                "所要查找的研究方面；不能只写论文标签，也不能只复述任务标题。"
                "不得引入题目没有出现的学科或应用领域。"
            )
        ),
    ]


class QueryDecompositionRetriever:
    def __init__(
        self,
        base_tool: BaseTool,
        queries: list[str],
        cached_result: str | None = None,
    ):
        if not 1 <= len(queries) <= MAX_DECOMPOSITION_QUERIES:
            raise ValueError("Query decomposition must contain 1 or 2 queries.")
        self.base_tool = base_tool
        self.queries = queries
        self.trace: list[dict[str, Any]] = []
        self._cached_result = cached_result

    @property
    def result(self) -> str | None:
        return self._cached_result

    @staticmethod
    def _source_files(result: str) -> list[str]:
        return sorted(
            set(re.findall(r"^\s+source_file:\s*(\S+)\s*$", result, re.MULTILINE))
        )

    @staticmethod
    def _evidence_count(result: str) -> int:
        match = re.search(
            r"returned_evidence_count:\s*(\d+)",
            result,
        )
        return int(match.group(1)) if match else 0

    @staticmethod
    def _result_text(result: Any) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, list):
            parts = []
            for block in result:
                if isinstance(block, dict) and isinstance(
                    block.get("text"),
                    str,
                ):
                    parts.append(block["text"])
                elif isinstance(getattr(block, "text", None), str):
                    parts.append(block.text)
                else:
                    parts.append(str(block))
            return "\n".join(parts)
        return str(result)

    async def retrieve(self, query: str, top_k: int = 4) -> str:
        if self._cached_result is not None:
            return self._cached_result

        sections = []
        all_sources: set[str] = set()
        total_evidence = 0
        for index, decomposed_query in enumerate(self.queries, start=1):
            started = time.perf_counter()
            try:
                result = await self.base_tool.ainvoke(
                    {
                        "query": decomposed_query,
                        "top_k": 4,
                    }
                )
                result_text = self._result_text(result)
                error = None
            except Exception as exc:
                result_text = ""
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - started
            sources = self._source_files(result_text)
            evidence_count = self._evidence_count(result_text)
            all_sources.update(sources)
            total_evidence += evidence_count
            self.trace.append(
                {
                    "query_index": index,
                    "query": decomposed_query,
                    "top_k": 4,
                    "mcp_tool": self.base_tool.name,
                    "source_filter_enabled": False,
                    "returned_evidence_count": evidence_count,
                    "source_files": sources,
                    "elapsed_seconds": round(elapsed, 6),
                    "error": error,
                }
            )
            sections.append(
                f"=== Decomposition Query {index} ===\n"
                f"query: {decomposed_query}\n"
                f"{result_text}"
            )

        header = (
            "Query decomposition executed through MCP tool "
            f"{self.base_tool.name}.\n"
            f"query_count: {len(self.queries)}\n"
            f"source_filter_enabled: false\n"
            f"unique_source_files: {sorted(all_sources)}\n"
            f"total_evidence_count: {total_evidence}\n"
            "source_coverage_status: "
            f"{'multi_source' if len(all_sources) >= 2 else 'single_or_no_source'}\n\n"
        )
        self._cached_result = header + "\n\n".join(sections)
        return self._cached_result

    def as_tool(self) -> StructuredTool:
        return StructuredTool.from_function(
            coroutine=self.retrieve,
            name=self.base_tool.name,
            description=self.base_tool.description,
        )


def validate_decomposition_plan(
    original_task: str,
    project_context: str,
    eligible: bool,
    queries: list[str],
) -> tuple[bool, list[str], str | None]:
    if not eligible:
        return False, [], None
    if _EXPLICIT_CROSS_SOURCE_CUE.search(original_task) is None:
        return (
            False,
            [],
            "task does not explicitly request cross-source comparison or synthesis",
        )
    cleaned = list(dict.fromkeys(query.strip() for query in queries if query.strip()))
    if len(cleaned) != 2:
        return False, [], "eligible plan did not contain two unique queries"
    if any(
        len(re.findall(r"\b\w+\b", query)) < 8
        or not query.rstrip().endswith("?")
        for query in cleaned
    ):
        return False, [], "one or more queries were too broad"
    task_tokens = set(re.findall(r"\b[a-z0-9]+\b", original_task.casefold()))
    context_tokens = set(
        re.findall(r"\b[a-z0-9]+\b", project_context.casefold())
    )
    for query in cleaned:
        query_tokens = set(re.findall(r"\b[a-z0-9]+\b", query.casefold()))
        introduced = (
            _UNGROUNDED_DOMAIN_TERMS.intersection(query_tokens)
            - task_tokens
            - context_tokens
        )
        if introduced:
            return (
                False,
                [],
                "query introduced ungrounded domain terms: "
                + ", ".join(sorted(introduced)),
            )
    return True, cleaned, None
