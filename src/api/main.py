"""IWF FastAPI application (Phase 5).

Exposes the LangGraph agent (Phase 4) through two endpoints:

- ``GET  /health``: health of the API and its subsystems (DuckDB,
  Ollama). Status ``ok`` or ``degraded`` based on availability.
- ``POST /chat``: one conversation turn. Delegates to the agent
  injected via ``get_agent_app`` and returns the text response
  with the session identifier (UUID4 generated if absent).

The application is built by the factory ``create_app()`` so tests
can use ``TestClient`` and ``dependency_overrides`` without
instantiating Ollama or touching the production database.

Startup (development):

    uvicorn src.api.main:app --host 0.0.0.0 --port 8000

or via the factory:

    uvicorn src.api.main:create_app --factory
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import duckdb
import requests
import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.api.config import get_settings
from src.api.dependencies import get_agent_app
from src.api.models import (
    ChatRequest,
    ChatResponse,
    ComponentHealth,
    HealthResponse,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """structlog log on startup and shutdown of the application."""
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
# Subsystem health checks
# ---------------------------------------------------------------------------


def _check_duckdb(path: str) -> ComponentHealth:
    """Checks that the DuckDB database is readable (SELECT 1)."""
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
    """Checks that the Ollama service responds (GET /api/tags, timeout 2s)."""
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
    """Builds and configures the FastAPI application (factory for tests).

    Returns:
        ``FastAPI`` instance with ``/health`` and ``/chat`` routes.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        """Sanity check of subsystems (DuckDB, Ollama)."""
        components = [
            _check_duckdb(settings.duckdb_path),
            _check_ollama(settings.ollama_url),
        ]
        overall: Literal["ok", "degraded"] = (
            "ok" if all(c.status == "ok" for c in components) else "degraded"
        )
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
        """One conversation turn with the agent.

        The payload is validated by Pydantic (``min_length=1``,
        ``max_length=2000``). If ``session_id`` is empty, a UUID4
        is generated server-side. Any exception from the agent is
        converted to ``HTTPException 500`` with a structlog log.
        The stacktrace never leaks.
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
                detail="Internal agent error.",
            ) from exc

        if not result.get("messages"):
            logger.error(
                "chat_empty_messages",
                session_id=session_id,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The agent produced no response.",
            )

        last = result["messages"][-1]
        text = last.content if isinstance(last.content, str) else str(last.content)
        return ChatResponse(response=text, session_id=session_id)

    return app


# Module-level singleton for `uvicorn src.api.main:app`.
app = create_app()


__all__ = ["create_app", "app", "lifespan"]