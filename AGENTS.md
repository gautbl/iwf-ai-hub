# AGENTS.md — IWF AI Hub

## Project Overview
Data + AI platform for the International Weightlifting Federation. Phases 1-5 : Docker infra, ETL dbt, RAG pipeline, LangGraph agent, FastAPI API. Phase 6 K8s deferred. 81 pytest tests green.

## Python Environnements (CRITICAL)
- `.venv` → ETL scripts, RAG, agent LangGraph (l API tourne aussi via Docker)
- dbt runs **inside** the Airflow container (dbt-duckdb installed via `Dockerfile.airflow`), **never** in a host venv
- PySpark (optional) runs in Docker or a dedicated `.venv-spark`. **Never** in `.venv`

## Conventions
- Python 3.11.9+, strict types
- Logs via structlog, never `print()`
- Config via pydantic-settings + ConfigMap K8s. Note: `src/agent/tools.py` and `src/agent/graph.py` also read `IWF_DUCKDB_PATH` and `IWF_OLLAMA_URL` via `os.environ.get`.
- One test per functional unit, pytest
- Formatting & linting via black + ruff (config in `pyproject.toml`)
- Type checking via mypy on the source code (`src/`)

## Forbidden (sovereignty)
- No managed cloud services (BigQuery, SageMaker, Bedrock)
- No LLM calls except Ollama locally
- No IWF data outside of the managed infrastructure

## Architecture
- **ETL**: Airflow → dbt → DuckDB (Star Schema)
- **RAG**: PDF → Chunking → Embeddings → DuckDB VSS → Agent
- **Agent**: LangGraph — retrieve → LLM → tools
- **API**: FastAPI — `/health`, `/chat`
- **Infra**: Docker Compose (dev) — Kubernetes (prod) deferred
  - Airflow : `Dockerfile.airflow`, port 8080
  - API : `Dockerfile.api`, port 8000
  - Ollama : image officielle, port 11434
- **Ingestion (optional)**: Airflow → MinIO (S3) + boto3 → Bronze
- **PySpark mirror (optional)**: Silver transformation + parity vs dbt

## Key Commands
- **Tests** : `pytest tests/` (unexpected warnings are errors via `filterwarnings` in `pyproject.toml`)
- **Lint + types + tests** : `ruff check src/ tests/ && black --check src/ tests/ && mypy src/ && pytest tests/`
- **Lint** : `ruff check src/ tests/`
- **Format** : `black src/ tests/`
- **Types** : `mypy src/`
- **Seed** : `scripts/seed_demo.sh` downloads TCRR PDF + CSV, initialises DB, loads chunks and embeddings
- **Startup verify** : `scripts/startup.sh` checks the DB, pulls Ollama models and rebuilds the HNSW VSS index
- **Docker** : `docker-compose up -d` starts Airflow (8080), API (8000), Ollama (11434)
- **Health check API** : `curl localhost:8000/health`
- **ETL** : Airflow DAG `iwf_performance_pipeline` at `http://localhost:8080`
- **dbt** (inside container) : `cd /opt/airflow/dbt && dbt run && dbt test`

## Critical Paths
- **DuckDB** : `data/duckdb/iwf_hub.duckdb` (gitignored) / `test_iwf_hub.duckdb`
- **Airflow DAGs** : `dags/` → `/opt/airflow/dags` in container
- **dbt models** : `dbt/models/` → `/opt/airflow/dbt/models`

## Warnings and pytest filtering

Two harmless upstream warnings are filtered (in `pyproject.toml` under `[tool.pytest.ini_options] filterwarnings`) :
- `LangChainPendingDeprecationWarning` (langgraph, `JsonPlusSerializer`) → `ignore::PendingDeprecationWarning:langgraph`
- `DeprecationWarning` anyio `BlockingPortal` (starlette testclient) → `ignore::DeprecationWarning:starlette.testclient`

The filter order is: `['error', 'ignore::PendingDeprecationWarning:langgraph', 'ignore::DeprecationWarning:starlette.testclient']`.
Unexpected warnings become errors, and the two upstream ones are ignored.

> **Note** : `pytest -W error tests/` does not work directly — pytest LIFO
order means the CLI flag is checked before the config ignores.
> Use `pytest tests/` (without `-W`) : `filterwarnings = ['error', ...]` provides
> equivalent protection.

## Environment Setup
- `.venv` exists on host. Deps from `requirements/base.txt`
- dbt runs in Airflow container (`Dockerfile.airflow`). Deps from `requirements/airflow.txt`
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
Project documentation and comments are in English. Code variable names are in English.