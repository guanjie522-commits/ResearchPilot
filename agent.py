import requests

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode


# =============================
# 1. 创建本地大模型和计算工具
# =============================

llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)


@tool
def calculator(a: float, b: float) -> float:
    """计算两个数字的乘积。遇到任何乘法计算时都必须使用这个工具。"""
    return a * b


@tool
def search_github(query: str) -> str:
    """查询 GitHub 项目或代码仓库。当用户寻找 GitHub 上的项目、仓库、开源实现或代码示例时使用。
    不要用于查询学术论文、科研证据或执行乘法计算。"""
    api_url = "https://api.github.com/search/repositories"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ResearchPilot",
    }
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 5,
    }

    try:
        response = requests.get(
            api_url,
            headers=headers,
            params=params,
            timeout=15,
        )
    except requests.RequestException as exc:
        return f"GitHub search failed: {exc.__class__.__name__}. Please try again later."

    if response.status_code != 200:
        if (
            response.status_code == 429
            or response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            return "GitHub API rate limit reached. Please try again later."
        return f"GitHub search failed: API returned HTTP {response.status_code}."

    try:
        data = response.json()
    except ValueError:
        return "GitHub search failed: API returned invalid JSON."

    repositories = data.get("items") or []
    if not repositories:
        return f"No GitHub repositories found for query: {query}"

    def clean_text(value, fallback: str) -> str:
        if value is None or value == "":
            return fallback
        return " ".join(str(value).split())

    results = []
    for index, repo in enumerate(repositories[:5], start=1):
        results.append(
            "\n".join(
                [
                    f"{index}. Repository: {clean_text(repo.get('full_name'), 'Unknown')}",
                    f"   Description: {clean_text(repo.get('description'), 'No description provided')}",
                    f"   Stars: {repo.get('stargazers_count', 0) or 0}",
                    f"   Language: {clean_text(repo.get('language'), 'Unknown')}",
                    f"   URL: {clean_text(repo.get('html_url'), 'Unavailable')}",
                ]
            )
        )

    return f"GitHub repositories for query '{query}':\n\n" + "\n\n".join(results)


@tool
def search_papers(query: str) -> str:
    """查询论文、学术研究和科研证据。当用户寻找研究论文、文献、学术成果或科学依据时使用。
    不要用于查询 GitHub 项目或执行乘法计算。"""
    return (
        "模拟论文搜索结果：\n"
        "1. Random-Field Effects in Antiferroelectric Materials（模拟论文）"
        " - 讨论随机场对反铁电材料的影响。\n"
        "2. Disorder and Phase Transitions in Ferroelectric Systems（模拟论文）"
        " - 综述无序和随机场相关的铁电相变研究。\n"
        f"搜索查询：{query}"
    )


tools = [calculator, search_github, search_papers]
llm_with_tools = llm.bind_tools(tools)


# =============================
# 2. 创建 Graph 的 Node
# =============================

def chatbot(state: MessagesState):

    response = llm_with_tools.invoke(
        [
            SystemMessage(
                content=(
                    "你是一个简洁、可靠的助手。"
                    "请根据用户意图以及每个工具的名称和 description 自行选择工具。"
                    "乘法计算使用 calculator；查询 GitHub 项目或仓库使用 search_github；"
                    "查询论文、学术研究或科研证据使用 search_papers。"
                    "乘法不要自己心算，问候或普通介绍直接回答，不需要调用工具。"
                )
            ),
            *state["messages"],
        ]
    )

    return {
        "messages": [response]
    }


def route_after_chatbot(state: MessagesState):
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END


# =============================
# 3. 创建 Graph
# =============================

builder = StateGraph(MessagesState)


# 添加节点
builder.add_node(
    "chatbot",
    chatbot,
)

builder.add_node(
    "tools",
    ToolNode(tools),
)


# START -> chatbot
builder.add_edge(
    START,
    "chatbot",
)


# chatbot -> tools 或 END
builder.add_conditional_edges(
    "chatbot",
    route_after_chatbot,
    {
        "tools": "tools",
        END: END,
    },
)


# tools -> chatbot
builder.add_edge(
    "tools",
    "chatbot",
)


# =============================
# 4. 编译 Graph
# =============================

graph = builder.compile()


# =============================
# 5. 运行并显示完整执行过程
# =============================

def run_test(label: str, user_input: str):
    print(f"\n{'=' * 60}")
    print(label)
    print(f"用户输入: {user_input}")

    initial_state = (
        {
            "messages": [
                HumanMessage(content=user_input),
            ]
        }
    )

    final_state = initial_state
    printed_message_count = 0
    tool_call_observed = False

    for state in graph.stream(initial_state, stream_mode="values"):
        final_state = state
        messages = state["messages"]

        while printed_message_count < len(messages):
            message = messages[printed_message_count]
            print(f"\n--- Message {printed_message_count + 1} ---")
            print(f"类型: {message.__class__.__name__}")

            if isinstance(message, HumanMessage):
                print(f"Content: {message.content}")

            elif isinstance(message, AIMessage):
                print(f"Content: {message.content!r}")

                if message.tool_calls:
                    tool_call_observed = True
                    print(f"是否包含 Tool Call: 是（共 {len(message.tool_calls)} 个）")

                    for tool_call in message.tool_calls:
                        print(f"Tool 名称: {tool_call['name']}")
                        print(f"Tool 参数: {tool_call['args']}")
                        print(f"Tool Call ID: {tool_call['id']}")
                else:
                    print("是否包含 Tool Call: 否")

            elif isinstance(message, ToolMessage):
                print(f"Tool Result: {message.content}")
                print(f"Tool Call ID: {message.tool_call_id}")

            printed_message_count += 1

    final_message = final_state["messages"][-1]

    if isinstance(final_message, AIMessage):
        print(f"\n最终 AIMessage 是否包含新的 Tool Call: {bool(final_message.tool_calls)}")
        print(f"最终 AI Answer: {final_message.content}")
    else:
        print(f"\n最终 Message 类型: {final_message.__class__.__name__}")

    return tool_call_observed


if __name__ == "__main__":
    run_test("测试 A", "请使用计算工具计算 237 × 489。")
    run_test("测试 B", "帮我找一下 LangGraph 相关的 GitHub 项目。")
    run_test("测试 C", "帮我找一下随机场影响反铁电材料的研究论文。")
    run_test("测试 D", "你好，请简单介绍一下你自己。")

