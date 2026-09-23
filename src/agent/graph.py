"""Graphe LangGraph de l'agent conversationnel IWF (Phase 4).

Trois nœuds : retrieve (recherche VSS des réglementations), agent
(génération de réponse via le LLM local Ollama) et tools (dispatch des
appels d'outils vers le registre TOOLS). Le checkpointer DuckDBSaver
persiste l'historique de session dans DuckDB.

Les fonctions de nœud sont définies au niveau module pour être testables
directement (les tests mockent ``_bound_llm`` et ``tools`` sans jamais
toucher un Ollama réel).
"""

import json
from typing import Any

import duckdb
import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.duckdb import DuckDBSaver
from langgraph.graph import END, START, StateGraph

from src.agent import tools
from src.agent.state import AgentState

logger = structlog.get_logger()

OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "llama3.2"

# LLM lié aux outils, injecté par build_graph avant compilation. Référencé
# au niveau module pour que les tests puissent le remplacer (monkeypatch).
_bound_llm: Any = None

# App compilée en cache (lazy singleton construit par get_app).
_app = None


def _wrap_tool(func, name: str) -> StructuredTool:
    """Enveloppe une fonction outil pour ChatOllama.bind_tools (note 4 de revue).

    Args:
        func: fonction outil du module src.agent.tools.
        name: nom d'outil, doit correspondre à une clé du registre TOOLS.

    Returns:
        StructuredTool prêt à être lié au LLM.
    """
    return StructuredTool.from_function(
        func=func, name=name, description=(func.__doc__ or "").strip()
    )


def retrieve_node(state: AgentState) -> dict:
    """Nœud de retrieval : recherche les extraits réglementaires pertinents.

    Extrait la dernière question humaine de la conversation et délègue à
    tools.search_regulations (VSS via src/pipelines/retrieval.py). En cas
    d'erreur, le nœud dégrade vers une liste vide sans faire planter le
    graphe.

    Args:
        state: état courant de l'agent.

    Returns:
        Dict avec la clé retrieved_docs (liste de chunks {chunk_text,
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
    """Nœud agent : génère la réponse via le LLM local.

    Si des chunks réglementaires ont été récupérés, ils sont injectés en
    tête de la conversation sous forme de SystemMessage de contexte. La
    réponse du LLM (éventuellement porteuse de tool_calls) est ajoutée
    aux messages.

    Args:
        state: état courant de l'agent.

    Returns:
        Dict avec la clé messages contenant la réponse du LLM.
    """
    messages = list(state["messages"])
    if state.get("retrieved_docs"):
        context = "\n".join(
            f"- {d.get('chunk_text', '')} "
            f"[{d.get('source', '')} | {d.get('article', '')} | p.{d.get('page', '')}]"
            for d in state["retrieved_docs"]
        )
        messages = [SystemMessage(content="Contexte réglementaire IWF :\n" + context)] + messages
    response = _bound_llm.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    """Nœud d'outils : dispatch des tool_calls vers le registre TOOLS.

    Chaque appel du dernier message (AIMessage) est exécuté via
    tools.TOOLS[name](**args). Le résultat est sérialisé en JSON dans un
    ToolMessage. Une exception d'outil est capturée et transformée en
    {"error": ...} : le graphe ne plante jamais sur un échec d'outil.

    Args:
        state: état courant de l'agent.

    Returns:
        Dict avec les clés messages (ToolMessages) et tool_calls (appels
        exécutés).
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
    """Routeur : renvoie "tools" si l'agent a émis des tool_calls, sinon "end".

    Args:
        state: état courant de l'agent.

    Returns:
        Nom de la destination : "tools" ou "end".
    """
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else "end"


def build_graph(db_path: str = tools.DB_PATH):
    """Construit et compile le graphe avec un checkpointer DuckDB sur db_path.

    Le LLM ChatOllama (llama3.2, endpoint local) est lié aux outils
    query_results et compute_athlete_stats ; search_regulations n'est PAS
    lié car le nœud retrieve possède la recherche. Le checkpointer
    DuckDBSaver est initialisé (setup) pour créer les tables de
    checkpoints avant compilation.

    Args:
        db_path: chemin de la base DuckDB (production par défaut).

    Returns:
        App LangGraph compilée, prête pour invoke.
    """
    global _bound_llm
    llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL)
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
    """Construit l'app une seule fois (lazy singleton) et la met en cache.

    Returns:
        App LangGraph compilée (mise en cache dans le module).
    """
    global _app
    if _app is None:
        _app = build_graph()
    return _app


def run(query: str, session_id: str) -> str:
    """Lance une session de l'agent et retourne la réponse finale.

    Args:
        query: question en langage naturel de l'utilisateur.
        session_id: identifiant de session, utilisé comme thread_id du
            checkpointer DuckDB (la mémoire de conversation persiste entre
            les appels d'un même thread).

    Returns:
        Contenu textuel du dernier message de la réponse.
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