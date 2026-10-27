# 01: Dockerise the FastAPI API

**What to build:** The IWF FastAPI API runs in `docker-compose up` with Airflow and Ollama. A `curl localhost:8000/health` returns 200 and shows DuckDB + Ollama in ok status.

**Blocked by:** None (can start immediately)

**Status:** done

## Work done

- [x] Create `Dockerfile.api` (base python:3.11-slim, pip install -e ., expose 8000)
- [x] Rename existing `Dockerfile` to `Dockerfile.airflow`
- [x] Add the `api` service in `docker-compose.yaml` with volume `data/duckdb:/data/duckdb`, dependency `ollama`, env vars `IWF_DUCKDB_PATH` and `IWF_OLLAMA_URL`
- [ ] Verify: `docker-compose up` + `curl localhost:8000/health` = 200 (needs Docker Engine)

## Source changes made

- `src/agent/graph.py` : `OLLAMA_BASE_URL` reads `IWF_OLLAMA_URL` from environment. New parameter `ollama_url` in `build_graph()`. Return type `CompiledStateGraph`.
- `src/agent/tools.py` : `DB_PATH` reads `IWF_DUCKDB_PATH` from environment.

## Verification

- 81 pytest tests green
- mypy + ruff pass
- 2 commits on `main` : `f384ccc` + `17b1160`