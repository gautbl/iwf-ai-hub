# AGENTS.md — IWF AI Hub

## Project Overview
Data + AI platform for the International Weightlifting Federation. Phases 1-3 complete (Docker infra, ETL dbt, RAG pipeline). Phase 4 (LangGraph agent) in progress.

## Python Environnements  (CRITICAL)
- `.venv`      → ETL scripts, RAG (Phase 3), API (Phase 5), agent LangGraph (Phase 4)
- dbt runs inside the Airflow container (dbt-duckdb installed via Dockerfile), **not** in a host venv.
  There is no `.venv-dbt` on the host.
- PySpark (Phase 2.5, optional) runs in Docker (`jupyter/pyspark-notebook`) or in a dedicated
  `.venv-spark` on the host (no Docker — requires a host JDK 11/17 with `JAVA_HOME`). **Never** in `.venv`.
Never install a dbt-only or PySpark dependency into `.venv`.

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
- **Ingestion (Phase 7, optional)**: Airflow → MinIO (S3-compatible, self-hosted) + boto3 → Bronze landing zone
- **PySpark mirror (Phase 2.5, optional)**: Silver transformation in PySpark (Docker) + parity validation vs dbt

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
2. `requirements/base.txt` holds only what's currently used: duckdb, numpy, pypdf, structlog,
   pandas, requests, reportlab, pytest.
3. dbt runs inside the Airflow container (installed via Dockerfile).
   `requirements/airflow.txt` (dbt-duckdb, pandas, requests, structlog) documents the container env.
4. Phase 4/5 deps (langchain, langchain-community, fastapi, uvicorn, pydantic)
   are already in base.txt; they were added ahead of those phases.
   Embeddings RAG passent par Ollama local (`nomic-embed-text`) ; sentence-transformers a été retiré.
5. Ollama runs separately for LLM/embeddings (port 11434)
6. DuckDB data persists via Docker volume mount
7. PySpark without Docker (optional): `requirements/spark.txt` builds a dedicated `.venv-spark`
   (pyspark, pandas, pyarrow, duckdb, jupyterlab). Prerequisite: JDK 11 or 17 with `JAVA_HOME` set.
   Exchange data with DuckDB via Parquet files (avoids storage-version coupling).

## dbt Quirks
- Project name must be `iwf_project` (matches `dbt_project.yml` and `profiles.yml`)
- `profiles.yml` path inside container: `/opt/airflow/dbt`
- Staging models materialized as views, marts as tables
- Raw tables prefixed with `raw_` (created by `extract_results.py`)

## Test Data
- ETL tests fetch from `https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv`
- SSL certificates handled via `certifi` in test files
- RAG tests create temporary PDFs using `reportlab`

## Current Status
- Phases 1-5 complete : Docker infra, ETL dbt, pipeline RAG, agent
  LangGraph (Phase 4), API FastAPI (Phase 5, 17 tests).
- Phase 6 in progress : manifests K8s (namespace, ConfigMap, Secret,
  ServiceAccount, PVC DuckDB) livrés, chart Helm + GitLab CI à venir.
- 58 tests pytest verts (`pytest tests/`).

## Known Issues / Phase 6 remaining
- Helm chart (`helm/iwf-ai-hub/`) — étape 6
- Ingress / HPA / NetworkPolicy — étape 6
- `.gitlab-ci.yml` — étape 7
- `notebooks/` (Phase 2.5) and `ingestion/` (Phase 7) not yet created (optional phases)

## Language
Project documentation and comments are in French. Code variable names are in English.