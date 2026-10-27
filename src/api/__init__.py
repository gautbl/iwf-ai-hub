"""Public entry point for the IWF FastAPI API (Phase 5).

Exposes configuration, Pydantic schemas and the FastAPI factory
(``create_app``). The singleton ``app`` also allows direct startup
via ``uvicorn src.api.main:app``.
"""

from src.api.config import Settings, get_settings
from src.api.dependencies import get_agent_app
from src.api.main import app, create_app
from src.api.models import (
    ChatRequest,
    ChatResponse,
    ComponentHealth,
    HealthResponse,
)

__all__ = [
    "Settings",
    "get_settings",
    "get_agent_app",
    "create_app",
    "app",
    "ChatRequest",
    "ChatResponse",
    "ComponentHealth",
    "HealthResponse",
]