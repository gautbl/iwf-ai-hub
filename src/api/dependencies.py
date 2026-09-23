"""Injection de dépendances de l'API FastAPI IWF (Phase 5).

Définit les ``Depends()`` consommés par les endpoints : l'application
LangGraph singleton et la configuration. En tests, ces dépendances
sont remplacées via ``app.dependency_overrides[...]`` pour ne jamais
toucher Ollama ou DuckDB.
"""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from src.agent.graph import get_app
from src.api.config import Settings, get_settings

__all__ = ["get_agent_app", "get_settings", "Settings"]


def get_agent_app() -> CompiledStateGraph:
    """Retourne l'application LangGraph compilée (singleton).

    Construit paresseusement au premier appel par
    ``src.agent.graph.get_app`` puis mis en cache dans le module
    agent. En production, le checkpointer DuckDB est configuré pour
    persister l'historique de session.

    En tests, cette dépendance est substituée via
    ``app.dependency_overrides[get_agent_app] = lambda: fake_app``
    pour éviter l'instanciation du LLM ou l'ouverture de la base.

    Returns:
        Application LangGraph compilée, prête pour ``invoke``.
    """
    return get_app()
