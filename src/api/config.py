"""Configuration of the IWF FastAPI API (Phase 5).

Parameters loaded via pydantic-settings, overridable by environment
variables prefixed with ``IWF_`` (e.g. ``IWF_PORT=8080``). These keys
inject into Kubernetes ConfigMaps in production.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the FastAPI application.

    Attributes:
        app_name: display name of the application.
        app_version: semver version of the API.
        host: listen interface (0.0.0.0 in container, 127.0.0.1 local).
        port: HTTP listen port.
        log_level: structlog log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        duckdb_path: path to the production DuckDB database.
        ollama_url: local Ollama endpoint for embeddings and LLM.
        llm_model: name of the local chat model (e.g. llama3.2).
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
    """Returns a single instance of the settings (clearable cache in tests).

    Returns:
        Settings instance loaded from the environment.
    """
    return Settings()