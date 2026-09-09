# AGENTS.md — IWF AI Hub

## Project Overview
Data + AI platform for the International Weightlifting Federation. Currently in active development (Phase 3: RAG pipeline in progress).

## Python Environnements  (CRITICAL)
- `.venv`      → ETL scripts, RAG (Phase 3), API (Phase 5), agent LangGraph (Phase 4)
- dbt runs inside the Airflow container (dbt-duckdb installed via Dockerfile), **not** in a host venv.
  There is no `.venv-dbt` on the host.
Never install a dbt-only dependency into `.venv`.

## Conventions
- Python 3.11+, strict types
- Logs via structlog, never print()
- Config via pydantic-settings + ConfigMap K8s
- One test per functional unit, pytest

## Forbidden (sovereignty)
- No managed cloud services (BigQuery, SageMaker, Bedrock)
- No LLM calls except Ollama locally
- No IWF data outside of the managed infrastructure

## Architecture Quick Reference
- **ETL**: Airflow → dbt → DuckDB (Star Schema)
- **RAG**: PDF → Chunking → Embeddings → DuckDB VSS → Agent
- **Agent**: LangGraph (not yet implemented)
- **API**: FastAPI (not yet implemented)
- **Infra**: Docker Compose (dev) → Kubernetes (prod)

## Key Commands

### Run ETL Pipeline
```bash
docker-compose up -d
# Airflow UI: http://localhost:8080
# DAG: iwf_performance_pipeline
```

### Run dbt Transformations (inside container)
```bash
cd /opt/airflow/dbt
dbt run
dbt test
```

### Run Tests
```bash
pytest tests/
```
Tests require network access (fetches CSV from GitHub for test data).

## Critical Paths
- **DuckDB file**: `data/duckdb/iwf_hub.duckdb` (gitignored, created by ETL)
- **Test DB**: `data/duckdb/test_iwf_hub.duckdb` (auto-created/cleaned by tests)
- **Airflow DAGs**: `dags/` (mounted to `/opt/airflow/dags` in container)
- **dbt models**: `dbt/models/` (mounted to `/opt/airflow/dbt/models`)

## Environment Setup
1. `.venv` exists on the host; deps come from `requirements/base.txt` (runtime list).
2. `requirements/base.txt` holds only what's currently used: duckdb, pandas, requests,
   reportlab, pytest, PyPDF2, certifi, structlog.
3. dbt runs inside the Airflow container (installed via Dockerfile).
   `requirements/airflow.txt` (dbt-duckdb, pandas, requests, structlog) documents the container env.
4. Phase 4/5 deps (langchain, langchain-community, fastapi, uvicorn, pydantic, sentence-transformers)
   are already in base.txt; they were added ahead of those phases.
5. Ollama runs separately for LLM/embeddings (port 11434)
6. DuckDB data persists via Docker volume mount

## dbt Quirks
- Project name must be `iwf_project` (matches `dbt_project.yml` and `profiles.yml`)
- `profiles.yml` path inside container: `/opt/airflow/dbt`
- Staging models materialized as views, marts as tables
- Raw tables prefixed with `raw_` (created by `extract_results.py`)

## Test Data
- ETL tests fetch from `https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv`
- SSL certificates handled via `certifi` in test files
- RAG tests create temporary PDFs using `reportlab`

## Known Issues
- `.gitlab-ci.yml` does not exist yet (Phase 6 planned)
- `src/pipelines/chunking.py` and `embeddings.py` exist but are untracked by git; `retrieval.py` is not yet created
- `src/agent/` and `src/api/` directories not yet created

## Language
Project documentation and comments are in French. Code variable names are in English.