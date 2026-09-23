"""Application FastAPI IWF (Phase 5).

Expose l'agent conversationnel LangGraph (Phase 4) au travers de
deux endpoints :

- ``GET  /health`` : état de l'API et de ses sous-systèmes (DuckDB,
  Ollama). Statut ``ok`` ou ``degraded`` selon la disponibilité.
- ``POST /chat``   : un tour de conversation. Délègue à l'agent
  injecté via ``get_agent_app`` et renvoie la réponse textuelle
  avec l'identifiant de session (UUID4 généré si absent).

L'application est construite par la factory ``create_app()`` afin de
permettre aux tests d'utiliser ``TestClient`` et ``dependency_overrides``
sans instancier Ollama ni toucher la base de production.

Lancement (développement) :

    uvicorn src.api.main:app --host 0.0.0.0 --port 8000

ou via la factory :

    uvicorn src.api.main:create_app --factory
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import duckdb
import requests
import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.api.config import Settings, get_settings
from src.api.dependencies import get_agent_app
from src.api.models import (
    ChatRequest,
    ChatResponse,
    ComponentHealth,
    HealthResponse,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Cycle de vie
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Log structlog au démarrage et à l'arrêt de l'application."""
    settings = get_settings()
    logger.info(
        "api_startup",
        app_name=settings.app_name,
        app_version=settings.app_version,
        duckdb_path=settings.duckdb_path,
        ollama_url=settings.ollama_url,
    )
    yield
    logger.info("api_shutdown")


# ---------------------------------------------------------------------------
# Health checks sous-systèmes
# ---------------------------------------------------------------------------


def _check_duckdb(path: str) -> ComponentHealth:
    """Vérifie que la base DuckDB est lisible (SELECT 1)."""
    try:
        conn = duckdb.connect(path, read_only=True)
        try:
            conn.execute("SELECT 1").fetchall()
        finally:
            conn.close()
        return ComponentHealth(name="duckdb", status="ok")
    except Exception as exc:
        return ComponentHealth(name="duckdb", status="degraded", detail=str(exc))


def _check_ollama(url: str) -> ComponentHealth:
    """Vérifie que le service Ollama répond (GET /api/tags, timeout 2 s)."""
    try:
        resp = requests.get(f"{url.rstrip('/')}/api/tags", timeout=2.0)
        resp.raise_for_status()
        return ComponentHealth(name="ollama", status="ok")
    except Exception as exc:
        return ComponentHealth(name="ollama", status="degraded", detail=str(exc))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Construit et configure l'application FastAPI (factory pour les tests).

    Returns:
        Instance de ``FastAPI`` avec les routes ``/health`` et ``/chat``.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        """Sanity check des sous-systèmes (DuckDB, Ollama)."""
        components = [
            _check_duckdb(settings.duckdb_path),
            _check_ollama(settings.ollama_url),
        ]
        overall = "ok" if all(c.status == "ok" for c in components) else "degraded"
        return HealthResponse(
            status=overall,
            app_name=settings.app_name,
            app_version=settings.app_version,
            components=components,
        )

    @app.post("/chat", response_model=ChatResponse, tags=["chat"])
    def chat(
        payload: ChatRequest,
        agent: CompiledStateGraph = Depends(get_agent_app),
    ) -> ChatResponse:
        """Un tour de conversation avec l'agent conversationnel.

        Le payload est validé par Pydantic (``min_length=1``,
        ``max_length=2000``). Si ``session_id`` est vide, un UUID4
        est généré côté serveur. Toute exception levée par
        l'agent est convertie en ``HTTPException 500`` avec un
        log structlog ; la stacktrace ne fuite jamais.
        """
        session_id = payload.session_id.strip() or str(uuid.uuid4())
        try:
            result = agent.invoke(
                {
                    "messages": [HumanMessage(content=payload.query)],
                    "retrieved_docs": [],
                    "tool_calls": [],
                    "session_id": session_id,
                },
                config={"configurable": {"thread_id": session_id}},
            )
        except Exception as exc:
            logger.error(
                "chat_invoke_error",
                session_id=session_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur interne de l'agent.",
            ) from exc

        if not result.get("messages"):
            logger.error(
                "chat_empty_messages",
                session_id=session_id,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="L'agent n'a produit aucune réponse.",
            )

        last = result["messages"][-1]
        text = last.content if isinstance(last.content, str) else str(last.content)
        return ChatResponse(response=text, session_id=session_id)

    return app


# Singleton au niveau module pour `uvicorn src.api.main:app`.
app = create_app()


__all__ = ["create_app", "app", "lifespan"]
