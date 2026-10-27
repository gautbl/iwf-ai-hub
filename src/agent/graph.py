"""LangGraph graph for the IWF conversational agent (Phase 4).

Three nodes: retrieve (VSS regulation search), agent
(response generation via local Ollama LLM) and tools (dispatch
of tool calls to the TOOLS registry). The DuckDBSaver checkpointer
persists session history in DuckDB.

Node functions are defined at module level to be testable
directly (tests mock ``_bound_llm`` and ``tools`` without ever
hitting a real Ollama).
"""

import json
import os
from typing import Any

import duckdb

# Replace the jsonplus module-level Reviver() (no explicit
# allowed_objects) with an instance using allowed_objects='core'.
# The default Reviver() constructor emits a
# LangChainPendingDeprecationWarning. This assignment makes sure the
# checkpointer internal code uses a correctly configured Reviver.
import langgraph.checkpoint.serde.jsonplus as _jp_jsonplus  # noqa: E402
import structlog
from langchain_core.load.load import Reviver
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.duckdb import DuckDBSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

_jp_jsonplus.LC_REVIVER = Reviver(allowed_objects="core")

from src.agent import tools
from src.agent.state import AgentState

logger = structlog.get_logger()

OLLAMA_BASE_URL = os.environ.get("IWF_OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = "llama3.2"

# LLM bound to tools, injected by build_graph before compilation. Lives
# at module level so tests can replace it (monkeypatch).
_bound_llm: Any = None

# Compiled app cache (lazy singleton built by get_app).
_app = None


def _wrap_tool(func, name: str) -> StructuredTool:
    """Wraps a tool function for ChatOllama.bind_tools (review note 4).

    Args:
        func: tool function from src.agent.tools module.
        name: tool name, must match a key in the TOOLS registry.

    Returns:
        StructuredTool ready to bind to the LLM.
    """
    return StructuredTool.from_function(
        func=func, name=name, description=(func.__doc__ or "").strip()
    )


def retrieve_node(state: AgentState) -> dict:
    """Retrieval node: searches for relevant regulation snippets.

    Extracts the last human question from the conversation and delegates to
    tools.search_regulations (VSS via src/pipelines/retrieval.py). On
    error, the node degrades to an empty list without crashing the
    graph.

    Args:
        state: current agent state.

    Returns:
        Dict with key retrieved_docs (list of chunks {chunk_text,
        source, article, page, score}).
    """
    query = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )
    try:
        docs = tools.search_regulations(str(query), 5)
    except Exception as exc:
        logger.error("retrieve_node_error", error=str(exc))
        docs = []
    return {"retrieved_docs": docs}


def agent_node(state: AgentState) -> dict:
    """Agent node: generates the response via the local LLM.

    If regulation chunks were retrieved, they inject at the
    head of the conversation as a SystemMessage context. The
    LLM response (possibly carrying tool_calls) appends to
    the messages.

    Args:
        state: current agent state.

    Returns:
        Dict with key messages containing the LLM response.
    """
    messages = list(state["messages"])
    if state.get("retrieved_docs"):
        context = "\n".join(
            f"- {d.get('chunk_text', '')} "
            f"[{d.get('source', '')} | {d.get('article', '')} | p.{d.get('page', '')}]"
            for d in state["retrieved_docs"]
        )
        messages = [
            SystemMessage(content="IWF regulatory context:\n" + context)
        ] + messages
    response = _bound_llm.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    """Tools node: dispatches tool_calls to the TOOLS registry.

    Each call from the last message (AIMessage) executes via
    tools.TOOLS[name](**args). The result serialises to JSON in a
    ToolMessage. A tool exception is caught and transformed to
    {"error": ...}: the graph never crashes on a tool failure.

    Args:
        state: current agent state.

    Returns:
        Dict with keys messages (ToolMessages) and tool_calls (executed
        calls).
    """
    executed: list[dict] = []
    new_messages: list[ToolMessage] = []
    for call in state["messages"][-1].tool_calls:
        try:
            result = tools.TOOLS[call["name"]](**call["args"])
        except Exception as exc:
            logger.error("tool_dispatch_error", tool=call["name"], error=str(exc))
            result = {"error": str(exc)}
        executed.append(call)
        new_messages.append(
            ToolMessage(
                content=json.dumps(result, ensure_ascii=False, default=str),
                tool_call_id=call["id"],
            )
        )
    return {"messages": new_messages, "tool_calls": executed}


def route(state: AgentState) -> str:
    """Router: returns "tools" if the agent emitted tool_calls, else "end".

    Args:
        state: current agent state.

    Returns:
        Destination name: "tools" or "end".
    """
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "end"


def build_graph(db_path: str = tools.DB_PATH, ollama_url: str | None = None) -> CompiledStateGraph:
    """Builds and compiles the graph with a DuckDB checkpointer on db_path.

    The ChatOllama LLM (llama3.2, local endpoint) binds to tools
    query_results and compute_athlete_stats. search_regulations is NOT
    bound because the retrieve node handles the search. The DuckDBSaver
    checkpointer initialises (setup) to create checkpoint tables
    before compilation.

    Args:
        db_path: path to the DuckDB database (production by default).

    Returns:
        Compiled LangGraph app, ready for invoke.
    """
    global _bound_llm
    llm = ChatOllama(model=LLM_MODEL, base_url=ollama_url or OLLAMA_BASE_URL)
    _bound_llm = llm.bind_tools(
        [
            _wrap_tool(tools.query_results, "query_results"),
            _wrap_tool(tools.compute_athlete_stats, "compute_athlete_stats"),
        ]
    )

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    conn = duckdb.connect(db_path)
    saver = DuckDBSaver(conn)
    saver.setup()
    return graph.compile(checkpointer=saver)


def get_app():
    """Builds the app once (lazy singleton) and caches it.

    Returns:
        Compiled LangGraph app (cached in the module).
    """
    global _app
    if _app is None:
        _app = build_graph()
    return _app


def run(query: str, session_id: str) -> str:
    """Runs an agent session and returns the final response.

    Args:
        query: natural language question from the user.
        session_id: session identifier, used as thread_id for the
            DuckDB checkpointer (conversation memory persists across
            calls from the same thread).

    Returns:
        Text content of the last response message.
    """
    app = get_app()
    result = app.invoke(
        {
            "messages": [HumanMessage(content=query)],
            "retrieved_docs": [],
            "tool_calls": [],
            "session_id": session_id,
        },
        config={"configurable": {"thread_id": session_id}},
    )
    content = result["messages"][-1].content
    return content if isinstance(content, str) else str(content)