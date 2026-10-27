"""Dependency injection for the IWF FastAPI API (Phase 5).

Defines the ``Depends()`` consumed by endpoints: the LangGraph
application singleton and the configuration. In tests, these
dependencies are replaced via ``app.dependency_overrides[...]``
to never touch Ollama or DuckDB.
"""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from src.agent.graph import get_app
from src.api.config import Settings, get_settings

__all__ = ["get_agent_app", "get_settings", "Settings"]


def get_agent_app() -> CompiledStateGraph:
    """Returns the compiled LangGraph application (singleton).

    Builds lazily on first call by ``src.agent.graph.get_app`` then
    caches in the agent module. In production, the DuckDB checkpointer
    persists session history.

    In tests, this dependency is replaced via
    ``app.dependency_overrides[get_agent_app] = lambda: fake_app``
    to avoid LLM instantiation or database opening.

    Returns:
        Compiled LangGraph application, ready for ``invoke``.
    """
    return get_app()