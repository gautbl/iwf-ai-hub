"""Point d'entrée public de l'API FastAPI IWF (Phase 5).

Expose la configuration, les schémas Pydantic et la fabrique de
l'application FastAPI (``create_app``). Le singleton ``app`` permet
aussi un lancement direct via ``uvicorn src.api.main:app``.
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
