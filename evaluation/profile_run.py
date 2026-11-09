import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fastmcp.client.transports import PythonStdioTransport
from langchain.mcp import MCPAdapter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.profiling import PerformanceProfiler, instrument_tools  # noqa: E402
from researchpilot_rag import (  # noqa: E402
    SERVER_PATH,
    build_research_graph,
    render_message_content,
    run_research,
    summarize,
)


DATASET_PATH = ROOT / "evaluation" / "dataset.json"
RESULTS_DIR = ROOT / "evaluation" / "results"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Profile ResearchPilot RAG graph")
    parser.add_argument(
        "--questions",
        default="q04,q10",
        help="Comma-separated question IDs",
    )
    parser.add_argument("--timeout", type=float, default=1200.0)
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    question_map = {
        item["question_id"]: item for item in dataset["questions"]
    }
    question_ids = [
        item.strip() for item in args.questions.split(",") if item.strip()
    ]
    questions = [question_map[item] for item in question_ids]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = RESULTS_DIR / f"profile_{run_id}.json"

    adapter = MCPAdapter(
        PythonStdioTransport(
            script_path=SERVER_PATH,
            python_cmd=sys.executable,
            cwd=SERVER_PATH.parent,
        )
    )
    profiler = PerformanceProfiler()
    profile_runs = []
    crossref_probe = None

    async with adapter:
        tools = await adapter.list_tools()
        profiled_tools = instrument_tools(tools, profiler)
        graph = build_research_graph(
            adapter.client,
            profiled_tools,
            profiler=profiler,
        )

        for question in questions:
            try:
                state = await asyncio.wait_for(
                    run_research(
                        graph,
                        question["question"],
                        f"Profile: {question['question_id']}",
                        profiler=profiler,
                    ),
                    timeout=args.timeout,
                )
                profile_runs.append(
                    {
                        "question_id": question["question_id"],
                        "question": question["question"],
                        "question_type": question["question_type"],
                        "run_status": "success",
                        "final_answer": state.get("final_answer", ""),
                        "citation_validation": state.get(
                            "citation_validation",
                            {},
                        ),
                        "tool_calls": [
                            {
                                "name": call["name"],
                                "args": call["args"],
                                "evidence_ids": call["evidence_ids"],
                            }
                            for result in state.get("step_results", [])
                            for call in result.get("tool_calls", [])
                        ],
                        "performance": state.get("performance", {}),
                    }
                )
            except Exception as exc:
                profile_runs.append(
                    {
                        "question_id": question["question_id"],
                        "question": question["question"],
                        "question_type": question["question_type"],
                        "run_status": (
                            "timeout"
                            if isinstance(exc, asyncio.TimeoutError)
                            else "error"
                        ),
                        "error_message": f"{type(exc).__name__}: {exc}",
                        "performance": profiler.snapshot(
                            {},
                            args.timeout
                            if isinstance(exc, asyncio.TimeoutError)
                            else 0.0,
                        ),
                    }
                )

        # One explicit Crossref probe records server-side request time without
        # adding another full Planner/Replanner run.
        search_papers = next(
            tool for tool in profiled_tools if tool.name == "search_papers"
        )
        probe_started = time.perf_counter()
        probe_result = await search_papers.ainvoke(
            {
                "query": "antiferroelectric energy storage",
                "max_results": 2,
            }
        )
        probe_elapsed = time.perf_counter() - probe_started
        probe_text = render_message_content(probe_result)
        request_seconds_match = re.search(
            r"Crossref request seconds:\s*([0-9.]+)",
            probe_text,
        )
        crossref_probe = {
            "mcp_tool_elapsed_seconds": round(probe_elapsed, 6),
            "crossref_api_seconds": (
                round(float(request_seconds_match.group(1)), 6)
                if request_seconds_match
                else None
            ),
            "result_summary": summarize(probe_text, 700),
        }

    payload = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_profile",
        "questions": question_ids,
        "profiles": profile_runs,
        "crossref_probe": crossref_probe,
        "notes": [
            "cold_start is determined from /api/ps before each run; null means unavailable.",
            "chroma_retrieval_seconds includes query embedding and Chroma retrieval.",
            "token fields are null when Ollama did not expose them.",
        ],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Profile result: {output_path}")
    for item in profile_runs:
        print(item["question_id"], item["run_status"])
        print(json.dumps(item.get("performance", {}), ensure_ascii=False, indent=2))
    print("Crossref probe:", json.dumps(crossref_probe, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
