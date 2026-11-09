from typing import Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from agent import graph as multi_tool_graph
from agent import llm


# =============================
# 1. State 与 Planner 输出结构
# =============================

class StepResult(TypedDict):
    step_number: int
    step: str
    result: str
    tool_calls: list[dict[str, Any]]


class ResearchState(TypedDict):
    original_task: str
    plan: list[str]
    current_step: int
    step_results: list[StepResult]
    final_answer: str


class PlanOutput(BaseModel):
    steps: list[str] = Field(
        min_length=2,
        max_length=4,
        description="按执行顺序排列的 2 到 4 个简洁、可执行步骤",
    )


planner_llm = llm.with_structured_output(PlanOutput, method="json_schema")


# =============================
# 2. Planner
# =============================

def planner_node(state: ResearchState):
    task = state["original_task"]

    plan_output = planner_llm.invoke(
        [
            SystemMessage(
                content=(
                    "你是 Research Planner。请把用户任务拆成 2 到 4 个按顺序执行的步骤。"
                    "只生成计划，不执行任务。每个步骤必须具体、可独立完成。"
                    "如果任务包含多个明确的研究方向，应分别安排信息检索步骤，"
                    "最后再安排一个汇总比较步骤，不能把所有方向合并成一个笼统步骤。"
                    "涉及最新外部信息的步骤应明确说明需要检索什么。"
                )
            ),
            HumanMessage(content=f"用户任务：{task}"),
        ]
    )

    plan = plan_output.steps
    print(f"\n用户 Original Task: {task}")
    print("\nPlanner 生成的完整 Plan:")
    for index, step in enumerate(plan, start=1):
        print(f"  {index}. {step}")

    return {
        "plan": plan,
        "current_step": 0,
        "step_results": [],
        "final_answer": "",
    }


# =============================
# 3. Executor
# =============================

def format_completed_results(step_results: list[StepResult]) -> str:
    if not step_results:
        return "暂无"

    return "\n\n".join(
        f"Step {item['step_number']}：{item['step']}\n结果：{item['result']}"
        for item in step_results
    )


def executor_node(state: ResearchState):
    plan = state["plan"]
    step_index = state["current_step"]
    current_step = plan[step_index]

    execution_prompt = (
        f"原始任务：{state['original_task']}\n\n"
        f"完整计划：\n"
        + "\n".join(
            f"{index}. {step}" for index, step in enumerate(plan, start=1)
        )
        + f"\n\n当前要执行的 Step {step_index + 1}：{current_step}\n\n"
        f"已完成步骤及结果：\n{format_completed_results(state['step_results'])}\n\n"
        "只执行当前 Step，不要提前执行后续 Step。"
        "请根据当前 Step 和工具 description 自行决定是否调用工具；"
        "需要最新或外部事实时不要凭空编造。"
        "完成当前 Step 后，用简洁的中文给出这一步的结果。"
    )

    execution_state = multi_tool_graph.invoke(
        {"messages": [HumanMessage(content=execution_prompt)]},
        config={"recursion_limit": 10},
    )
    execution_messages = execution_state["messages"]

    tool_calls = []
    for message in execution_messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_calls.append(
                    {
                        "name": tool_call["name"],
                        "args": tool_call["args"],
                        "id": tool_call["id"],
                    }
                )

    final_message = execution_messages[-1]
    if not isinstance(final_message, AIMessage):
        raise RuntimeError("Executor 未以 AIMessage 结束。")

    step_result = str(final_message.content)
    next_step_index = step_index + 1

    print(f"\n当前执行 Step 编号: {step_index + 1}/{len(plan)}")
    print(f"当前 Step 内容: {current_step}")
    print(f"当前 Step 是否调用 Tool: {'是' if tool_calls else '否'}")
    for tool_call in tool_calls:
        print(f"Tool 名称: {tool_call['name']}")
        print(f"Tool 参数: {tool_call['args']}")

    print("\n当前 Step 的工具返回:")
    tool_messages = [
        message for message in execution_messages if isinstance(message, ToolMessage)
    ]
    if tool_messages:
        for tool_message in tool_messages:
            print(tool_message.content)
    else:
        print("未调用工具")

    print(f"\n当前 Step Result: {step_result}")

    updated_results: list[StepResult] = [
        *state["step_results"],
        {
            "step_number": step_index + 1,
            "step": current_step,
            "result": step_result,
            "tool_calls": tool_calls,
        },
    ]

    return {
        "current_step": next_step_index,
        "step_results": updated_results,
    }


def route_after_executor(state: ResearchState):
    has_next_step = state["current_step"] < len(state["plan"])
    print(f"是否还有下一 Step: {'是' if has_next_step else '否'}")
    return "executor" if has_next_step else "writer"


# =============================
# 4. Writer
# =============================

def writer_node(state: ResearchState):
    plan_text = "\n".join(
        f"{index}. {step}" for index, step in enumerate(state["plan"], start=1)
    )
    results_text = format_completed_results(state["step_results"])

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "你是 Research Writer。请综合原始任务、计划和各步骤结果来回答。"
                    "只使用提供的步骤结果，不要重新执行或声称调用了工具，不要编造事实。"
                    "回答应简洁清楚，并完成用户要求的比较或总结。"
                )
            ),
            HumanMessage(
                content=(
                    f"原始任务：{state['original_task']}\n\n"
                    f"完整计划：\n{plan_text}\n\n"
                    f"步骤结果：\n{results_text}"
                )
            ),
        ]
    )

    final_answer = str(response.content)
    print(f"\nFinal Answer:\n{final_answer}")

    return {"final_answer": final_answer}


# =============================
# 5. Graph
# =============================

builder = StateGraph(ResearchState)
builder.add_node("planner", planner_node)
builder.add_node("executor", executor_node)
builder.add_node("writer", writer_node)

builder.add_edge(START, "planner")
builder.add_edge("planner", "executor")
builder.add_conditional_edges(
    "executor",
    route_after_executor,
    {
        "executor": "executor",
        "writer": "writer",
    },
)
builder.add_edge("writer", END)

research_graph = builder.compile()


# =============================
# 6. 运行入口
# =============================

def run_research(task: str) -> ResearchState:
    initial_state: ResearchState = {
        "original_task": task,
        "plan": [],
        "current_step": 0,
        "step_results": [],
        "final_answer": "",
    }

    final_state = initial_state
    for state in research_graph.stream(initial_state, stream_mode="values"):
        final_state = state

    return final_state


if __name__ == "__main__":
    run_research(
        "帮我调研 GitHub 上值得学习的 AI Agent 开源项目，分别关注 "
        "Agent Framework、Memory 和 Evaluation 三个方向，并给出简单比较。"
    )
