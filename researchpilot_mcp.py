import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal, TypedDict

from fastmcp.client.transports import PythonStdioTransport
from langchain.mcp import MCPAdapter
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field


SERVER_PATH = Path(__file__).with_name("research_mcp_server.py")
PROJECT_CONTEXT_URI = "project://researchpilot/context"
MAX_REPLAN_COUNT = 8
MAX_EXECUTED_STEPS = 8


class ToolCallRecord(TypedDict):
    name: str
    args: dict[str, Any]
    result_summary: str


class StepResult(TypedDict):
    step_number: int
    step: str
    result: str
    tool_calls: list[ToolCallRecord]


class ResearchState(TypedDict):
    original_task: str
    project_context: str
    plan: list[str]
    current_step: int
    completed_steps: list[str]
    step_results: list[StepResult]
    replan_count: int
    final_answer: str
    replanner_action: str
    replanner_reason: str


class PlanOutput(BaseModel):
    steps: list[str] = Field(
        min_length=2,
        max_length=4,
        description="按执行顺序排列的 2 到 4 个简洁、可执行步骤",
    )


class ReplanDecision(BaseModel):
    action: Literal["continue", "update", "finish"] = Field(
        description="下一步动作：继续、更新剩余计划或结束"
    )
    reason: str = Field(description="做出该决策的具体理由")
    updated_remaining_steps: list[str] = Field(
        default_factory=list,
        description="仅 action=update 时提供的新的剩余步骤，不包含已完成步骤",
    )


llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)
writer_llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)
writer_retry_llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)
planner_llm = llm.with_structured_output(PlanOutput, method="json_schema")
replanner_llm = llm.with_structured_output(ReplanDecision, method="json_schema")


def render_message_content(content: Any) -> str:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
            else:
                text_parts.append(str(block))
        text = "\n".join(text_parts)
    else:
        text = str(content)
    return re.sub(
        r"<think\b[^>]*>.*?</think\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()


def summarize(text: str, limit: int = 900) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."


def format_completed_steps(step_results: list[StepResult]) -> str:
    if not step_results:
        return "暂无"
    sections = []
    for item in step_results:
        tool_evidence = "\n".join(
            f"MCP Tool {tool_call['name']} {tool_call['args']} "
            "返回摘要："
            + summarize(
                tool_call["result_summary"],
                1800 if tool_call["name"] == "search_papers" else 350,
            )
            for tool_call in item["tool_calls"]
        )
        sections.append(
            f"Step {item['step_number']}：{item['step']}\n"
            f"结果摘要：{summarize(item['result'], 500)}\n"
            f"工具证据：{tool_evidence or '本步骤未调用工具'}"
        )
    return "\n\n".join(sections)


def format_writer_step_results(step_results: list[StepResult]) -> str:
    sections = []
    for item in step_results:
        source_lines = []
        for tool_call in item["tool_calls"]:
            if tool_call["name"] != "search_papers":
                source_lines.append(
                    f"{tool_call['name']} 返回摘要："
                    + summarize(tool_call["result_summary"], 350)
                )
                continue

            current: dict[str, str] = {}
            for line in tool_call["result_summary"].splitlines():
                title_match = re.match(r"\s*\d+\.\s+Title:\s*(.+)", line)
                if title_match:
                    if current.get("title"):
                        source_lines.append(
                            "论文元数据："
                            f"{current['title']} | 年份：{current.get('year', '未知')} "
                            f"| 期刊：{current.get('journal', '未知')} "
                            f"| DOI：{current.get('doi', '未知')} "
                            f"| URL：{current.get('url', '未知')}"
                        )
                    current = {"title": title_match.group(1).strip()}
                    continue
                field_match = re.match(
                    r"\s+(Publication Year|Journal|DOI|URL):\s*(.+)",
                    line,
                )
                if field_match:
                    key = {
                        "Publication Year": "year",
                        "Journal": "journal",
                        "DOI": "doi",
                        "URL": "url",
                    }[field_match.group(1)]
                    current[key] = field_match.group(2).strip()
            if current.get("title"):
                source_lines.append(
                    "论文元数据："
                    f"{current['title']} | 年份：{current.get('year', '未知')} "
                    f"| 期刊：{current.get('journal', '未知')} "
                    f"| DOI：{current.get('doi', '未知')} "
                    f"| URL：{current.get('url', '未知')}"
                )

        sections.append(
            f"Step {item['step_number']}：{item['step']}\n"
            f"步骤结果：{summarize(item['result'], 500)}\n"
            f"来源元数据：\n"
            + ("\n".join(source_lines) if source_lines else "本步骤未调用工具")
        )
    return "\n\n".join(sections)


def build_executor_agent(mcp_tools: list[BaseTool]):
    executor_llm = llm.bind_tools(mcp_tools)

    async def executor_chatbot(state: MessagesState):
        response = await executor_llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是 ResearchPilot Executor。只执行用户给出的当前 Step。"
                        "根据工具 description 自行决定是否调用 MCP Tool。"
                        "如果当前 Step 明确要求执行 GitHub 搜索或给出了 GitHub 查询，"
                        "必须优先调用 search_github，而不是自行声称搜索结果。"
                        "如果当前 Step 要求检索学术论文、研究文献或文献主题，"
                        "必须调用 search_papers，不能用 search_github 代替。"
                        "工具返回后，仅总结返回值中真实存在的项目和信息。"
                        "不要加入无关仓库、README、issue、测试或维护状态。"
                        "没有工具返回数据时，不得列出或编造任何仓库。"
                        "论文摘要缺失时必须保留“摘要缺失”的事实，"
                        "不得根据标题编造摘要或声称阅读了论文全文。"
                        "不要用普通文本打印工具调用 JSON；需要使用工具时调用原生 Tool。"
                        "证据不足时明确说明，不要猜测。"
                    )
                ),
                *state["messages"],
            ]
        )
        return {"messages": [response]}

    def route_after_executor_chatbot(state: MessagesState):
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    executor_builder = StateGraph(MessagesState)
    executor_builder.add_node("chatbot", executor_chatbot)
    executor_builder.add_node("tools", ToolNode(mcp_tools))
    executor_builder.add_edge(START, "chatbot")
    executor_builder.add_conditional_edges(
        "chatbot",
        route_after_executor_chatbot,
        {
            "tools": "tools",
            END: END,
        },
    )
    executor_builder.add_edge("tools", "chatbot")
    return executor_builder.compile()


def build_research_graph(mcp_client, mcp_tools: list[BaseTool]):
    executor_agent = build_executor_agent(mcp_tools)

    async def context_loader_node(state: ResearchState):
        print(f"\nOriginal Task: {state['original_task']}")
        print(f"Resource URI: {PROJECT_CONTEXT_URI}")
        print("正在通过 MCP Client 读取项目 Resource...")

        contents = await mcp_client.read_resource(PROJECT_CONTEXT_URI)
        text_parts = [
            content.text
            for content in contents
            if isinstance(getattr(content, "text", None), str)
        ]
        if not text_parts:
            raise RuntimeError("MCP Resource 未返回文本内容。")

        project_context = "\n".join(text_parts)
        print(f"Resource Content 摘要: {summarize(project_context, 500)}")
        return {
            "project_context": project_context,
            "plan": [],
            "current_step": 0,
            "completed_steps": [],
            "step_results": [],
            "replan_count": 0,
            "final_answer": "",
            "replanner_action": "",
            "replanner_reason": "",
        }

    async def planner_node(state: ResearchState):
        plan_output = await planner_llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是 ResearchPilot Planner，只负责制定计划，不执行任务、不调用工具。"
                        "请根据用户任务和项目 Resource 背景，生成 2 到 4 个按顺序可执行的步骤。"
                        "利用项目背景识别当前学习进度，避免再次规划已经完成的学习阶段。"
                        "若任务包含多个明确调研方向，必须为每个方向分别安排独立检索步骤，"
                        "不能把多个方向合并到同一个检索步骤中；最后保留综合比较步骤。"
                        "学术论文和文献检索步骤应明确要求使用 Crossref 论文元数据；"
                        "只有用户同时要求 GitHub 项目时才安排 GitHub 仓库检索。"
                        "计划应聚焦本任务需要的新信息，不要重复搭建已完成能力。"
                        "使用中文输出计划。"
                    )
                ),
                HumanMessage(
                    content=(
                        f"用户任务：{state['original_task']}\n\n"
                        f"项目 Resource：\n{state['project_context']}"
                    )
                ),
            ]
        )
        plan = plan_output.steps

        print("\nInitial Plan:")
        for index, step in enumerate(plan, start=1):
            print(f"  {index}. {step}")
        return {"plan": plan, "current_step": 0}

    async def executor_node(state: ResearchState):
        plan = state["plan"]
        step_index = state["current_step"]

        if step_index >= len(plan):
            return {}

        current_step = plan[step_index]

        print(f"\nCurrent Step: {step_index + 1}/{len(plan)}")
        print(f"Step 内容: {current_step}")

        execution_state = await executor_agent.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            f"原始任务：{state['original_task']}\n\n"
                            "当前项目阶段：MCP Resource\n\n"
                            f"当前 Step：{current_step}\n\n"
                            "已有证据：\n"
                            + format_completed_steps(state["step_results"])
                            + "\n\n只输出当前 Step 的简洁结果。"
                        )
                    )
                ]
            },
            config={"recursion_limit": 10},
        )

        messages = execution_state["messages"]
        if not any(
            isinstance(message, AIMessage) and message.tool_calls
            for message in messages
        ):
            final_text = (
                render_message_content(messages[-1].content)
                if isinstance(messages[-1], AIMessage)
                else ""
            )
            try:
                textual_call = json.loads(
                    final_text.strip().removeprefix("```json").removesuffix("```").strip()
                )
            except (ValueError, TypeError):
                textual_call = None
            if (
                isinstance(textual_call, dict)
                and isinstance(textual_call.get("name"), str)
                and (
                    isinstance(textual_call.get("arguments"), dict)
                    or isinstance(textual_call.get("args"), dict)
                )
            ):
                print(
                    "Executor Guard: 模型输出了文本形式 Tool Call，"
                    "将进行一次原生 Tool Call 纠正重试。"
                )
                execution_state = await executor_agent.ainvoke(
                    {
                        "messages": [
                            *messages,
                            HumanMessage(
                                content=(
                                    "你刚才把工具调用写成了普通文本。"
                                    "不要输出 JSON 文本；如果当前 Step 需要外部检索，"
                                    "请立即发起原生 MCP Tool Call。"
                                )
                            ),
                        ]
                    },
                    config={"recursion_limit": 10},
                )
                messages = execution_state["messages"]

        tool_calls: list[ToolCallRecord] = []
        tool_messages_by_call_id = {
            message.tool_call_id: message
            for message in messages
            if isinstance(message, ToolMessage)
        }

        for message in messages:
            if not isinstance(message, AIMessage) or not message.tool_calls:
                continue
            for tool_call in message.tool_calls:
                matching_result = tool_messages_by_call_id.get(tool_call["id"])
                result_text = (
                    render_message_content(matching_result.content)
                    if matching_result is not None
                    else ""
                )
                record: ToolCallRecord = {
                    "name": tool_call["name"],
                    "args": tool_call["args"],
                    "result_summary": summarize(
                        result_text,
                        5000 if tool_call["name"] == "search_papers" else 900,
                    ),
                }
                tool_calls.append(record)
                print("\nMCP Tool Call: 是")
                print(f"Tool Name: {tool_call['name']}")
                print(f"Tool Args: {tool_call['args']}")
                print(f"MCP Tool Result 摘要: {summarize(result_text, 500)}")
                if tool_call["name"] == "search_papers":
                    status_line = next(
                        (
                            line
                            for line in result_text.splitlines()
                            if line.startswith("Crossref request status:")
                        ),
                        "Crossref request status: unavailable",
                    )
                    print(status_line)
                    current_title = ""
                    for line in result_text.splitlines():
                        title_match = re.match(
                            r"\s*\d+\.\s+Title:\s*(.+)",
                            line,
                        )
                        if title_match:
                            current_title = title_match.group(1).strip()
                            continue
                        doi_match = re.match(r"\s+DOI:\s*(\S+)", line)
                        if current_title and doi_match:
                            print(
                                f"Paper: {summarize(current_title, 180)} "
                                f"| DOI: {doi_match.group(1)}"
                            )
                            current_title = ""

        if not tool_calls:
            print("\nMCP Tool Call: 否")

        final_message = messages[-1]
        if not isinstance(final_message, AIMessage):
            raise RuntimeError("Executor 未以 AIMessage 结束。")
        step_result = render_message_content(final_message.content)
        tool_result_texts = [
            render_message_content(message.content)
            for message in messages
            if isinstance(message, ToolMessage)
        ]
        if tool_result_texts:
            repository_names = {
                repository.strip()
                for text in tool_result_texts
                for repository in re.findall(
                    r"(?m)^\s*\d+\.\s+Repository:\s+([^\n]+)",
                    text,
                )
            }
            if repository_names and not any(
                repository in step_result for repository in repository_names
            ):
                step_result = (
                    "MCP Tool 实际返回的仓库结果：\n"
                    + summarize("\n".join(tool_result_texts), 1200)
                )
                print(
                    "Step Result Guard: 模型总结未引用本次 MCP 返回的任何仓库，"
                    "已改用真实 MCP Tool 返回值。"
                )
            doi_values = {
                doi.strip()
                for text in tool_result_texts
                for doi in re.findall(r"(?m)^\s+DOI:\s*(\S+)", text)
            }
            if doi_values and not any(doi in step_result for doi in doi_values):
                step_result = (
                    "MCP Tool 实际返回的论文结果：\n"
                    + summarize("\n".join(tool_result_texts), 4000)
                )
                print(
                    "Step Result Guard: 模型总结未引用本次 MCP 返回的任何论文 DOI，"
                    "已改用真实 MCP Tool 返回值。"
                )

        updated_results: list[StepResult] = [
            *state["step_results"],
            {
                "step_number": step_index + 1,
                "step": current_step,
                "result": step_result,
                "tool_calls": tool_calls,
            },
        ]

        print(f"Step Result: {summarize(step_result, 700)}")
        return {
            "current_step": step_index + 1,
            "completed_steps": [*state["completed_steps"], current_step],
            "step_results": updated_results,
            "replanner_action": "",
            "replanner_reason": "",
        }

    async def replanner_node(state: ResearchState):
        remaining_steps = state["plan"][state["current_step"] :]
        decision = await replanner_llm.ainvoke(
            [
                SystemMessage(
                    content=(
                        "你是 ResearchPilot Replanner。请评估刚完成的 Executor 结果和剩余计划，"
                        "从 continue、update、finish 中选择一个动作。"
                        "continue：剩余计划仍然合适；update：基于新结果必须调整剩余步骤，"
                        "并给出完整的新剩余步骤；finish：原任务已经可以充分回答。"
                        "只有剩余计划没有实质问题时才 continue；"
                        "只有确实出现新的缺口、方向或比较需求时才 update，"
                        "不要为了改写措辞而 update。"
                        "如果刚完成的步骤发现了具体候选项目或新的证据缺口，"
                        "而剩余计划没有安排针对性核实，应使用 update 补充必要的后续步骤。"
                        "新增步骤必须能够由当前已发现的 MCP Tools 实际执行；"
                        "不要规划需要 README、issue、PR、测试覆盖或贡献者数据，"
                        "而当前 Tools 无法提供这些数据的核实步骤。"
                        "在原任务的每个明确调研方向都至少有一个独立 Step Result 之前，"
                        "不能选择 finish。"
                        "论文任务只需要 Crossref 元数据，不要规划 PDF 下载或全文解析。"
                        "不要重复已完成步骤，不要调用工具。"
                    )
                ),
                HumanMessage(
                    content=(
                        f"原始任务：{state['original_task']}\n\n"
                        f"项目 Resource：\n{state['project_context']}\n\n"
                        f"当前完整计划：\n"
                        + "\n".join(
                            f"{index}. {step}"
                            for index, step in enumerate(state["plan"], start=1)
                        )
                        + "\n\n已完成步骤：\n"
                        + (
                            "\n".join(state["completed_steps"])
                            if state["completed_steps"]
                            else "暂无"
                        )
                        + "\n\n步骤结果：\n"
                        + format_completed_steps(state["step_results"])
                        + "\n\n当前剩余计划：\n"
                        + (
                            "\n".join(remaining_steps)
                            if remaining_steps
                            else "暂无"
                        )
                    )
                ),
            ]
        )

        replan_count = state["replan_count"] + 1
        action = decision.action
        reason = decision.reason
        new_plan = state["plan"]

        if replan_count >= MAX_REPLAN_COUNT:
            action = "finish"
            reason = f"Reached max replan count ({MAX_REPLAN_COUNT}) guardrail."
        elif state["current_step"] >= MAX_EXECUTED_STEPS:
            action = "finish"
            reason = f"Reached max executed steps ({MAX_EXECUTED_STEPS}) guardrail."
        elif state["current_step"] >= len(state["plan"]):
            if action != "finish":
                reason = (
                    f"All planned steps are complete; replacing {action} with finish. "
                    f"Original reason: {reason}"
                )
            action = "finish"
        elif action == "update":
            updated_steps = [
                step.strip()
                for step in decision.updated_remaining_steps
                if step.strip()
            ]
            if updated_steps:
                new_plan = [*state["completed_steps"], *updated_steps]
            else:
                action = "continue"
                reason = (
                    "Replanner requested update without new remaining steps; "
                    f"keeping current plan. Original reason: {reason}"
                )

        remaining_after_decision = new_plan[state["current_step"] :]
        print(f"\nReplanner Decision: {action}")
        print(f"Replanner Reason: {reason}")
        print(
            "Remaining Plan:\n"
            + (
                "\n".join(
                    f"  - {step}" for step in remaining_after_decision
                )
                if remaining_after_decision
                else "  - 无"
            )
        )

        return {
            "plan": new_plan,
            "replan_count": replan_count,
            "replanner_action": action,
            "replanner_reason": reason,
        }

    def route_after_replanner(state: ResearchState):
        if state["replanner_action"] in {"continue", "update"}:
            return "executor"
        return "writer"

    async def writer_node(state: ResearchState):
        writer_messages = [
            SystemMessage(
                content=(
                    "你是 ResearchPilot Writer。只根据用户任务、项目 Resource、"
                    "已完成步骤和步骤结果生成最终回答。"
                    "不要调用工具，不要重新调研，不要编造步骤结果中没有的事实。"
                    "如果步骤结果同时包含模型总结和 MCP Tool 返回摘要，"
                    "应优先使用可验证的 Tool 返回摘要。"
                    "不要把未出现在 Tool 返回中的 README、issue、测试或维护状态"
                    "描述为已验证事实。"
                    "对于论文，只能使用 Crossref 元数据，不得声称阅读了论文全文，"
                    "也不得为缺失摘要补充内容。"
                    "论文推荐应保留真实 DOI 或来源 URL。"
                    "回答应清楚综合多个 Step Result，并给出用户要求的最终建议。"
                )
            ),
            HumanMessage(
                content=(
                    f"原始任务：{state['original_task']}\n\n"
                    f"项目 Resource：\n{state['project_context']}\n\n"
                    f"已完成步骤：\n"
                    + "\n".join(
                        f"{index}. {step}"
                        for index, step in enumerate(
                            state["completed_steps"], start=1
                        )
                    )
                    + "\n\n步骤结果：\n"
                    + format_writer_step_results(state["step_results"])
                )
            ),
        ]
        try:
            response = await writer_llm.ainvoke(writer_messages)
        except Exception as exc:
            if "token repeat limit" not in str(exc):
                raise
            print(
                "\nWriter Guard: qwen3:4b 触发 token repeat limit，"
                "使用更强的重复惩罚进行一次重试。"
            )
            response = await writer_retry_llm.ainvoke(writer_messages)
        final_answer = render_message_content(response.content)
        print(f"\nFinal Answer:\n{final_answer}")
        return {"final_answer": final_answer}

    builder = StateGraph(ResearchState)
    builder.add_node("context_loader", context_loader_node)
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("replanner", replanner_node)
    builder.add_node("writer", writer_node)

    builder.add_edge(START, "context_loader")
    builder.add_edge("context_loader", "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "replanner")
    builder.add_conditional_edges(
        "replanner",
        route_after_replanner,
        {
            "executor": "executor",
            "writer": "writer",
        },
    )
    builder.add_edge("writer", END)
    return builder.compile()


async def run_research(research_graph, original_task: str, label: str):
    print(f"\n{'=' * 78}")
    print(label)
    initial_state: ResearchState = {
        "original_task": original_task,
        "project_context": "",
        "plan": [],
        "current_step": 0,
        "completed_steps": [],
        "step_results": [],
        "replan_count": 0,
        "final_answer": "",
        "replanner_action": "",
        "replanner_reason": "",
    }

    final_state = initial_state
    async for state in research_graph.astream(
        initial_state,
        stream_mode="values",
        config={"recursion_limit": 40},
    ):
        final_state = state
    return final_state


async def run_executor_only_test(executor_agent, user_input: str, label: str):
    print(f"\n{'=' * 78}")
    print(label)
    print(f"HumanMessage: {user_input}")

    state = await executor_agent.ainvoke(
        {"messages": [HumanMessage(content=user_input)]},
        config={"recursion_limit": 10},
    )
    for message in state["messages"][1:]:
        if isinstance(message, AIMessage):
            print(f"AIMessage: {message.content!r}")
            for tool_call in message.tool_calls:
                print("AI Tool Call: 是")
                print(f"Tool Name: {tool_call['name']}")
                print(f"Tool Args: {tool_call['args']}")
            if not message.tool_calls:
                print("AI Tool Call: 否")
        elif isinstance(message, ToolMessage):
            print(
                "MCP Tool Result: "
                + summarize(render_message_content(message.content), 700)
            )
    return state


async def main():
    transport = PythonStdioTransport(
        script_path=SERVER_PATH,
        python_cmd=sys.executable,
        cwd=SERVER_PATH.parent,
    )
    adapter = MCPAdapter(transport)

    print("正在建立本次 ResearchPilot 运行使用的 MCP stdio 会话...")
    async with adapter:
        mcp_tools = await adapter.list_tools()
        resources = await adapter.client.list_resources()

        print("MCP Server 连接成功（本次运行复用此会话）")
        print("实际发现的 MCP Tools:")
        for tool in mcp_tools:
            print(f"  - {tool.name}: {tool.description}")
            print(
                "    Parameters: "
                + json.dumps(tool.args, ensure_ascii=False)
            )

        discovered_tool_names = {tool.name for tool in mcp_tools}
        required_tools = {"calculator", "search_github", "search_papers"}
        if not required_tools.issubset(discovered_tool_names):
            raise RuntimeError(
                f"缺少必要的 MCP Tools: {sorted(required_tools - discovered_tool_names)}"
            )

        discovered_resource_uris = {str(resource.uri) for resource in resources}
        if PROJECT_CONTEXT_URI not in discovered_resource_uris:
            raise RuntimeError(f"缺少必要 MCP Resource: {PROJECT_CONTEXT_URI}")

        print("实际发现的 MCP Resources:")
        for resource in resources:
            print(
                f"  - {resource.uri} ({resource.name}, {resource.mime_type})"
            )

        research_graph = build_research_graph(adapter.client, mcp_tools)
        await run_research(
            research_graph,
            (
                "帮我检索 antiferroelectric energy storage 相关的学术论文，"
                "列出论文标题、年份、期刊和 DOI。"
            ),
            "Test A: Real Paper Search",
        )
        await run_research(
            research_graph,
            (
                "帮我调研 phase-field simulation dielectric breakdown "
                "相关的研究文献，并整理值得进一步阅读的论文。"
            ),
            "Test B: Paper Research + Planner + Replanning",
        )

        executor_agent = build_executor_agent(mcp_tools)
        await run_executor_only_test(
            executor_agent,
            "帮我搜索 LangGraph 的 GitHub 仓库。",
            "Test C: GitHub Tool Routing",
        )
        await run_executor_only_test(
            executor_agent,
            "请使用计算工具计算 237 × 489。",
            "Test D: Calculator Regression",
        )


if __name__ == "__main__":
    asyncio.run(main())
