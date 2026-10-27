"""Public entry point for the IWF LangGraph conversational agent (Phase 4).

This module exposes only the `run` function (execute a user query)
and the `AgentState` type (graph state). All other internal symbols
stay private.
"""

from src.agent.graph import run
from src.agent.state import AgentState

__all__ = ["run", "AgentState"]
