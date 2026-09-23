"""Configuration de l'API FastAPI IWF (Phase 5).

Paramètres chargés via pydantic-settings, surchargeables par variables
d'environnement préfixées par ``IWF_`` (ex: ``IWF_PORT=8080``). Ces clés
seront injectées dans les ConfigMaps Kubernetes en production.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application FastAPI.

    Attributes:
        app_name: nom affiché de l'application.
        app_version: version semver de l'API.
        host: interface d'écoute (0.0.0.0 en conteneur, 127.0.0.1 en local).
        port: port d'écoute HTTP.
        log_level: niveau de log structlog (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        duckdb_path: chemin vers la base DuckDB de production.
        ollama_url: endpoint local Ollama pour embeddings et LLM.
        llm_model: nom du modèle de chat local (ex: llama3.2).
    """

    model_config = SettingsConfigDict(
        env_prefix="IWF_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "IWF AI Hub API"
    app_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    duckdb_path: str = "data/duckdb/iwf_hub.duckdb"
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique des paramètres (cache clairable en tests).

    Returns:
        Instance de Settings chargée depuis l'environnement.
    """
    return Settings()
