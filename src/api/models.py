"""Schémas Pydantic de l'API FastAPI IWF (Phase 5).

Définit les modèles de requêtes et de réponses consommés par les
endpoints. Validation stricte via Pydantic v2 (hérité de FastAPI) avec
contraintes ``min_length`` / ``max_length`` pour borner les payloads et
éviter les abus.

Tous les modèles sont sérialisables en JSON ; ils alimentent
automatiquement le schéma OpenAPI exposé par FastAPI sur ``/docs``.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ComponentHealth(BaseModel):
    """État d'un composant vérifié par l'endpoint ``/health``.

    Attributes:
        name: nom logique du composant (ex: ``duckdb``, ``ollama``).
        status: ``ok`` si le composant répond, ``degraded`` sinon.
        detail: message complémentaire (erreur ou information).
    """

    name: str
    status: Literal["ok", "degraded"]
    detail: str = ""


class HealthResponse(BaseModel):
    """Réponse de l'endpoint ``/health``.

    Attributes:
        status: ``ok`` si tous les composants répondent, ``degraded``
            sinon (l'API reste utilisable mais un sous-système est KO).
        app_name: nom affiché de l'application.
        app_version: version semver de l'API.
        components: état détaillé de chaque sous-système vérifié.
    """

    status: Literal["ok", "degraded"]
    app_name: str
    app_version: str
    components: list[ComponentHealth] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Requête utilisateur pour l'endpoint ``POST /chat``.

    Attributes:
        query: question en langage naturel (1 à 2000 caractères).
        session_id: identifiant de session pour la mémoire
            conversationnelle. Optionnel et vide par défaut ; le
            endpoint génère un UUID4 si la chaîne est vide.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question en langage naturel de l'utilisateur.",
    )
    session_id: str = Field(
        default="",
        max_length=128,
        description=(
            "Identifiant de session (UUID4 ou nom logique). Vide = nouvelle session."
        ),
    )

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        """Rejette les requêtes composées uniquement d'espaces ou de sauts de ligne.

        Pydantic ``min_length=1`` accepte les chaînes blanchâtres ; ce
        validator les refuse pour éviter que le LLM ne reçoive une
        question vide après ``strip()``.
        """
        if not value.strip():
            raise ValueError("query ne peut pas être uniquement composée d'espaces.")
        return value


class ChatResponse(BaseModel):
    """Réponse de l'agent pour l'endpoint ``POST /chat``.

    Attributes:
        response: contenu textuel de la réponse finale du LLM.
        session_id: identifiant de session effectivement utilisé
            (renvoyé tel quel ou généré si vide à l'entrée).
    """

    response: str = Field(..., description="Réponse textuelle finale de l'agent.")
    session_id: str = Field(..., description="ID de session (entrée ou nouveau UUID4).")
