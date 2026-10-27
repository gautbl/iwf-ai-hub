# AGENTS.md — IWF AI Hub

## Project Overview
Data + AI platform for the International Weightlifting Federation. Phases 1-5 : Docker infra, ETL dbt, pipeline RAG, agent LangGraph, API FastAPI. Phase 6 K8s reportée. 81 tests pytest verts.

## Python Environnements (CRITICAL)
- `.venv` → ETL scripts, RAG, API, agent LangGraph
- dbt runs **inside** the Airflow container (dbt-duckdb installed via Dockerfile), **never** in a host venv
- PySpark (optional) runs in Docker or a dedicated `.venv-spark`. **Never** in `.venv`

## Conventions
- Python 3.11.9+, strict types
- Logs via structlog, never `print()`
- Config via pydantic-settings + ConfigMap K8s
- One test per functional unit, pytest
- Formatting & linting via black + ruff (config dans `pyproject.toml`)
- Type checking via mypy sur le code source (`src/`)

## Forbidden (sovereignty)
- No managed cloud services (BigQuery, SageMaker, Bedrock)
- No LLM calls except Ollama locally
- No IWF data outside of the managed infrastructure

## Architecture
- **ETL**: Airflow → dbt → DuckDB (Star Schema)
- **RAG**: PDF → Chunking → Embeddings → DuckDB VSS → Agent
- **Agent**: LangGraph — retrieve → LLM → tools
- **API**: FastAPI — `/health`, `/chat`
- **Infra**: Docker Compose (dev) — Kubernetes (prod) reporté
- **Ingestion (optional)**: Airflow → MinIO (S3) + boto3 → Bronze
- **PySpark mirror (optional)**: Silver transformation + parity vs dbt

## Key Commands
- **Tests** : `pytest tests/` (les warnings inattendus sont en erreur via `filterwarnings` dans `pyproject.toml`)
- **Lint + types + tests** : `ruff check src/ tests/ && black --check src/ tests/ && mypy src/ && pytest tests/`
- **Lint** : `ruff check src/ tests/`
- **Format** : `black src/ tests/`
- **Types** : `mypy src/`
- **ETL** : `docker-compose up -d` → Airflow UI http://localhost:8080, DAG `iwf_performance_pipeline`
- **dbt** (inside container) : `cd /opt/airflow/dbt && dbt run && dbt test`

## Critical Paths
- **DuckDB** : `data/duckdb/iwf_hub.duckdb` (gitignored) / `test_iwf_hub.duckdb`
- **Airflow DAGs** : `dags/` → `/opt/airflow/dags` in container
- **dbt models** : `dbt/models/` → `/opt/airflow/dbt/models`

## Warnings et filtrage pytest

Deux avertissements amont inoffensifs sont filtrés (dans `pyproject.toml` sous `[tool.pytest.ini_options] filterwarnings`) :
- `LangChainPendingDeprecationWarning` (langgraph, `JsonPlusSerializer`) → `ignore::PendingDeprecationWarning:langgraph`
- `DeprecationWarning` anyio `BlockingPortal` (starlette testclient) → `ignore::DeprecationWarning:starlette.testclient`

L'ordre des filtres est : `['error', 'ignore::PendingDeprecationWarning:langgraph', 'ignore::DeprecationWarning:starlette.testclient']`.
Les warnings inattendus sont donc en erreur, et les deux amont sont ignorés.

> **Note** : `pytest -W error tests/` ne fonctionne pas directement — l'ordre LIFO
de pytest fait que le flag CLI est vérifié avant les ignores du config.
> Utiliser `pytest tests/` (sans `-W`) : le `filterwarnings = ['error', ...]` fournit
> une protection équivalente.

## Environment Setup
- `.venv` exists on host ; deps from `requirements/base.txt`
- dbt runs in Airflow container ; deps from `requirements/airflow.txt`
- Ollama runs separately (port 11434) for LLM + embeddings (`nomic-embed-text`)
- DuckDB data persists via Docker volume mount
- PySpark (optional) : `requirements/spark.txt` → `.venv-spark`, JDK 11/17 required, exchange via Parquet

## dbt
- Project name : `iwf_project`
- `profiles.yml` inside container : `/opt/airflow/dbt`
- Staging = views, marts = tables, raw tables prefixed `raw_`

## Agent skills

### Issue tracker
Issues tracked as local markdown files under `.scratch/`. Conventions : `docs/agents/issue-tracker.md`.

### Triage labels
Five canonical labels mapping to local tracker strings : `docs/agents/triage-labels.md`.

### Domain docs
Single-context layout : one `GLOSSARY.md` + `docs/adr/` at root. Rules : `docs/agents/domain.md`.

## Language
Project documentation and comments are in French. Code variable names are in English.