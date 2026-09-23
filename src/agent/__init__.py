"""Point d'entrée public de l'agent conversationnel LangGraph IWF (Phase 4).

Ce module expose uniquement la fonction `run` (exécution d'une requête
utilisateur) et le type `AgentState` (état du graphe). Tout autre symbole
interne reste privé.
"""

from src.agent.graph import run
from src.agent.state import AgentState

__all__ = ["run", "AgentState"]