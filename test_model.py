from langchain_ollama import ChatOllama


llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)


response = llm.invoke(
    "你好，请用一句非常简单的话解释什么是 AI Agent。"
)


print(response.content)