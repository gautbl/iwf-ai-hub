"""Pydantic schemas for the IWF FastAPI API (Phase 5).

Defines request and response models consumed by the endpoints.
Strict validation via Pydantic v2 (inherited from FastAPI) with
``min_length`` / ``max_length`` constraints to bound payloads and
prevent abuse.

All models are JSON-serialisable. They automatically populate the
OpenAPI schema exposed by FastAPI at ``/docs``.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ComponentHealth(BaseModel):
    """State of a component checked by the ``/health`` endpoint.

    Attributes:
        name: logical component name (e.g. ``duckdb``, ``ollama``).
        status: ``ok`` if the component responds, ``degraded`` otherwise.
        detail: additional message (error or information).
    """

    name: str
    status: Literal["ok", "degraded"]
    detail: str = ""


class HealthResponse(BaseModel):
    """Response of the ``/health`` endpoint.

    Attributes:
        status: ``ok`` if all components respond, ``degraded``
            otherwise (the API remains usable but a subsystem is KO).
        app_name: display name of the application.
        app_version: semver version of the API.
        components: detailed state of each checked subsystem.
    """

    status: Literal["ok", "degraded"]
    app_name: str
    app_version: str
    components: list[ComponentHealth] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """User request for the ``POST /chat`` endpoint.

    Attributes:
        query: natural language question (1 to 2000 characters).
        session_id: session identifier for conversation memory.
            Optional and empty by default. The endpoint generates a
            UUID4 if the string is empty.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question from the user.",
    )
    session_id: str = Field(
        default="",
        max_length=128,
        description=(
            "Session identifier (UUID4 or logical name). Empty = new session."
        ),
    )

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        """Rejects queries made only of spaces or line breaks.

        Pydantic ``min_length=1`` accepts whitespace-only strings. This
        validator rejects them so the LLM does not receive an empty
        question after ``strip()``.
        """
        if not value.strip():
            raise ValueError("query cannot be composed only of spaces.")
        return value


class ChatResponse(BaseModel):
    """Agent response for the ``POST /chat`` endpoint.

    Attributes:
        response: text content of the final LLM response.
        session_id: session identifier actually used
            (returned as-is or generated if empty on input).
    """

    response: str = Field(..., description="Final text response from the agent.")
    session_id: str = Field(..., description="Session ID (input or new UUID4).")