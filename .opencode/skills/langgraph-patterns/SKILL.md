---
name: langgraph-patterns
description: LangGraph agent patterns for the IWF conversational agent (phase 4)
---

## State definition
```python
class AgentState(TypedDict):
    messages:       Annotated[list, add_messages]
    retrieved_docs: list[dict]
    tool_calls:     list[dict]
    session_id:     str
```

## Graph skeleton
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.duckdb import DuckDBSaver

graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_node)
graph.add_node("agent",    agent_node)
graph.add_node("tools",    tool_node)

graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "agent")
graph.add_conditional_edges(
    "agent", route, {"tools": "tools", "end": END}
)
graph.add_edge("tools", "agent")

checkpointer = DuckDBSaver.from_conn_string("data/duckdb/iwf_hub.duckdb")
app = graph.compile(checkpointer=checkpointer)
```

## Nodes
| Node | Role | Source file |
|---|---|---|
| retrieve | VSS search in chunks table | src/pipelines/retrieval.py |
| agent | Response generation via local LLM | ChatOllama llama3.2 |
| tools | Dispatch to registered tools | src/agent/tools.py |

## Registered tools (src/agent/tools.py)
| Tool | Input | Output |
|---|---|---|
| search_regulations | query: str, top_k: int = 5 | list[dict] |
| query_results | athlete_name, category_name, event_date | list[dict] |
| compute_athlete_stats | athlete_name: str | dict |

## LLM
- Model: llama3.2 (lightest Ollama model, optimized for Apple Silicon M-series)
- Binding: langchain-ollama ChatOllama
- Endpoint: http://localhost:11434 only
- Never use a remote LLM

## Checkpointer
- DuckDBSaver connected to data/duckdb/iwf_hub.duckdb
- Checkpoint tables created automatically by LangGraph
- No MemorySaver, no SQLite

## Routing logic
```python
def route(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"
```

## Public interface (src/agent/graph.py)
```python
def run(query: str, session_id: str) -> str:
    """Run one agent turn and return the final response."""
```

## Project constraints
- LLM via local Ollama only (ChatOllama, model llama3.2)
- Retrieval node calls src/pipelines/retrieval.py only, never a remote store
- Conversation content never persists outside managed infrastructure
- Python environment: .venv exclusively

## Critical pitfalls
- DuckDBSaver requires duckdb >= 0.10.0 and langgraph-checkpoint-duckdb
- The HNSW index is not persistent across DuckDB sessions: reload on startup
- session_id must be passed as config to app.invoke: app.invoke(input, config={"configurable": {"thread_id": session_id}})
- Mock ChatOllama in all unit tests; never hit a live Ollama instance

## Testing
- One unit test per node (mock LLM, mock retrieval)
- One graph-level integration test (mock LLM, real test_iwf_hub.duckdb)
- Follow pytest-conventions skill for cleanup and isolation
