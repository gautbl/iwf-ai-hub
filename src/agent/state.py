"""Etat de l'agent conversationnel IWF (LangGraph, Phase 4).

Définit le schéma d'état partagé par les nœuds du graphe : messages
(conversation), retrieved_docs (chunks VSS), tool_calls (appels d'outils)
et session_id (thread du checkpointer DuckDB).
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """État partagé par les nœuds du graphe LangGraph.

    Attributes:
        messages: historique de la conversation (messages LangChain).
            La clé est annotée avec le reducer ``add_messages`` : les
            nouveaux messages sont concaténés à l'historique existant
            au lieu de le remplacer.
        retrieved_docs: chunks réglementaires récupérés par le nœud de
            retrieval VSS, au format {chunk_text, source, article,
            page, score} (sortie de src/pipelines/retrieval.py).
        tool_calls: appels d'outils émis par l'agent et leurs résultats
            (query_results, compute_athlete_stats).
        session_id: identifiant de session utilisé comme thread_id par
            le checkpointer DuckDBSaver.
    """

    messages: Annotated[list, add_messages]
    retrieved_docs: list[dict]
    tool_calls: list[dict]
    session_id: str
