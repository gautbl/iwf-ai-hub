"""State of the IWF conversational agent (LangGraph, Phase 4).

Defines the shared state schema used by graph nodes: messages
(conversation), retrieved_docs (VSS chunks), tool_calls (tool calls)
and session_id (DuckDB checkpointer thread).
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State shared by the LangGraph graph nodes.

    Attributes:
        messages: conversation history (LangChain messages).
            The key uses the ``add_messages`` reducer: new messages
            concatenate to the existing history instead of replacing it.
        retrieved_docs: regulation chunks from the VSS retrieval node,
            format {chunk_text, source, article, page, score} (output
            of src/pipelines/retrieval.py).
        tool_calls: tool calls made by the agent and their results
            (query_results, compute_athlete_stats).
        session_id: session id used as thread_id by the DuckDBSaver
            checkpointer.
    """

    messages: Annotated[list, add_messages]
    retrieved_docs: list[dict]
    tool_calls: list[dict]
    session_id: str
