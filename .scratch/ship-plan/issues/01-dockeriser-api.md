# 01: Dockeriser l'API FastAPI

**What to build:** L'API FastAPI IWF tourne dans `docker-compose up` avec Airflow et Ollama. Un `curl localhost:8000/health` retourne 200 et montre DuckDB + Ollama en status ok.

**Blocked by:** None (can start immediately)

**Status:** done

## Travail realise

- [x] Creer `Dockerfile.api` (base python:3.11-slim, pip install -e ., expose 8000)
- [x] Renommer `Dockerfile` existant en `Dockerfile.airflow`
- [x] Ajouter le service `api` dans `docker-compose.yaml` avec le volume `data/duckdb:/data/duckdb`, dependance `ollama`, variables `IWF_DUCKDB_PATH` et `IWF_OLLAMA_URL`
- [ ] Verifier : `docker-compose up` + `curl localhost:8000/health` = 200 (necessite Docker Engine)

## Modifications source accompagnees

- `src/agent/graph.py` : `OLLAMA_BASE_URL` lit `IWF_OLLAMA_URL` depuis l'environnement. Nouveau parametre `ollama_url` dans `build_graph()`. Type de retour `CompiledStateGraph`.
- `src/agent/tools.py` : `DB_PATH` lit `IWF_DUCKDB_PATH` depuis l'environnement.

## Verification

- 81 tests pytest verts
- mypy + ruff passent
- 2 commits sur `main` : `f384ccc` + `17b1160`