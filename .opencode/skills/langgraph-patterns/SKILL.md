---
name: langgraph-patterns
description: LangGraph agent patterns for the IWF conversational agent (phase 4)
---

## State definition
```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retrieved_docs: list[dict]
    tool_calls: list[dict]
```

## Graph skeleton
```python
graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "agent")
graph.add_conditional_edges("agent", route, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")
```

## Project constraints
- LLM via local Ollama only (langchain-ollama ChatOllama)
- Retrieval node must call src/pipelines/retrieval.py, never a remote vector store
- Checkpointer for memory: MemorySaver in dev, SQLite in prod
- Never persist conversation content outside managed infrastructure

## Testing
- One test per node (unit) plus one graph-level test (integration)
- Mock the LLM; never hit a real Ollama instance in unit tests
