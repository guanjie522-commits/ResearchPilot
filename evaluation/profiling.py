import time
import re
from collections import defaultdict
from typing import Any

import requests
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import BaseTool, StructuredTool


class PerformanceProfiler(BaseCallbackHandler):
    def __init__(self, model_name: str = "qwen3:4b") -> None:
        super().__init__()
        self.model_name = model_name
        self.reset()

    def reset(self) -> None:
        self.node_seconds: dict[str, float] = defaultdict(float)
        self.node_calls: dict[str, int] = defaultdict(int)
        self.tool_seconds: dict[str, float] = defaultdict(float)
        self.tool_calls: dict[str, int] = defaultdict(int)
        self.llm_call_count = 0
        self.llm_error_count = 0
        self.llm_wall_seconds = 0.0
        self.llm_generation_seconds: float | None = None
        self.prompt_tokens: int | None = None
        self.completion_tokens: int | None = None
        self.total_tokens: int | None = None
        self.chroma_retrieval_seconds = 0.0
        self.crossref_api_seconds = 0.0
        self.generation_model_loaded_before_run: bool | None = None
        self.cold_start: bool | None = None
        self._llm_started: dict[str, float] = {}
        self._generation_model_loaded_at_run_start()

    def _generation_model_loaded_at_run_start(self) -> None:
        try:
            response = requests.get("http://localhost:11434/api/ps", timeout=2)
            response.raise_for_status()
            models = response.json().get("models") or []
            names = [str(item.get("name") or item.get("model") or "") for item in models]
            self.generation_model_loaded_before_run = any(
                name == self.model_name or name.startswith(self.model_name + ":")
                for name in names
            )
            self.cold_start = not self.generation_model_loaded_before_run
        except Exception:
            self.generation_model_loaded_before_run = None
            self.cold_start = None

    def record_node(self, name: str, seconds: float) -> None:
        self.node_seconds[name] += seconds
        self.node_calls[name] += 1

    def record_tool(self, name: str, seconds: float) -> None:
        self.tool_seconds[name] += seconds
        self.tool_calls[name] += 1

    def record_internal_timings(self, tool_name: str, text: str) -> None:
        if tool_name == "retrieve_paper_evidence":
            match = re.search(
                r"retrieval_seconds[:=]\s*([0-9.]+)",
                text,
            )
            if match:
                self.chroma_retrieval_seconds += float(match.group(1))
        elif tool_name == "search_papers":
            match = re.search(
                r"Crossref request seconds:\s*([0-9.]+)",
                text,
            )
            if match:
                self.crossref_api_seconds += float(match.group(1))

    def on_llm_start(self, serialized, prompts, *, run_id, **kwargs) -> None:
        self.llm_call_count += 1
        self._llm_started[str(run_id)] = time.perf_counter()

    def on_llm_end(self, response, *, run_id, **kwargs) -> None:
        started = self._llm_started.pop(str(run_id), None)
        if started is not None:
            self.llm_wall_seconds += time.perf_counter() - started

        for generation_list in getattr(response, "generations", []):
            for generation in generation_list:
                message = getattr(generation, "message", None)
                if message is None:
                    continue
                usage = getattr(message, "usage_metadata", None) or {}
                response_metadata = (
                    getattr(message, "response_metadata", None) or {}
                )
                prompt_count = usage.get("input_tokens") or response_metadata.get(
                    "prompt_eval_count"
                )
                completion_count = usage.get(
                    "output_tokens"
                ) or response_metadata.get("eval_count")
                total_count = usage.get("total_tokens")
                if isinstance(prompt_count, int):
                    self.prompt_tokens = (self.prompt_tokens or 0) + prompt_count
                if isinstance(completion_count, int):
                    self.completion_tokens = (
                        (self.completion_tokens or 0) + completion_count
                    )
                if isinstance(total_count, int):
                    self.total_tokens = (self.total_tokens or 0) + total_count
                elif isinstance(prompt_count, int) and isinstance(
                    completion_count,
                    int,
                ):
                    self.total_tokens = (
                        (self.total_tokens or 0)
                        + prompt_count
                        + completion_count
                    )
                total_duration_ns = response_metadata.get("total_duration")
                if isinstance(total_duration_ns, int):
                    seconds = total_duration_ns / 1_000_000_000
                    self.llm_generation_seconds = (
                        (self.llm_generation_seconds or 0.0) + seconds
                    )

    def on_llm_error(self, error, *, run_id, **kwargs) -> None:
        self._llm_started.pop(str(run_id), None)
        self.llm_error_count += 1

    def snapshot(self, state: dict[str, Any], total_seconds: float) -> dict[str, Any]:
        return {
            "total_seconds": round(total_seconds, 6),
            "planner_seconds": round(self.node_seconds["planner"], 6),
            "executor_seconds": round(self.node_seconds["executor"], 6),
            "replanner_seconds": round(self.node_seconds["replanner"], 6),
            "writer_seconds": round(self.node_seconds["writer"], 6),
            "context_loader_seconds": round(
                self.node_seconds["context_loader"],
                6,
            ),
            "mcp_tool_seconds": {
                name: round(seconds, 6)
                for name, seconds in sorted(self.tool_seconds.items())
            },
            "mcp_tool_total_seconds": round(sum(self.tool_seconds.values()), 6),
            "chroma_retrieval_seconds": round(
                self.chroma_retrieval_seconds,
                6,
            ),
            "crossref_api_seconds": round(self.crossref_api_seconds, 6),
            "llm_call_count": self.llm_call_count,
            "llm_error_count": self.llm_error_count,
            "llm_wall_seconds": round(self.llm_wall_seconds, 6),
            "llm_generation_seconds": (
                round(self.llm_generation_seconds, 6)
                if self.llm_generation_seconds is not None
                else None
            ),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "token_metadata_status": (
                "available"
                if self.total_tokens is not None
                else "unavailable"
            ),
            "tool_call_count": sum(self.tool_calls.values()),
            "tool_calls_by_name": dict(sorted(self.tool_calls.items())),
            "executed_steps": self.node_calls["executor"],
            "replanning_count": state.get("replan_count", 0),
            "generation_model_loaded_before_run": (
                self.generation_model_loaded_before_run
            ),
            "cold_start": self.cold_start,
            "node_call_counts": dict(sorted(self.node_calls.items())),
        }


def instrument_tools(
    tools: list[BaseTool],
    profiler: PerformanceProfiler,
) -> list[BaseTool]:
    profiled = []
    for original in tools:
        async def timed_call(_original=original, **kwargs):
            started = time.perf_counter()
            result = await _original.ainvoke(kwargs)
            profiler.record_tool(
                _original.name,
                time.perf_counter() - started,
            )
            return result

        profiled.append(
            StructuredTool.from_function(
                coroutine=timed_call,
                name=original.name,
                description=original.description or "",
                args_schema=original.args_schema,
                response_format="content",
                metadata=original.metadata,
            )
        )
    return profiled
