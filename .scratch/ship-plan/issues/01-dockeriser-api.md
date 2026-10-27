# 01: Dockeriser l'API FastAPI

**What to build:** L'API FastAPI IWF tourne dans `docker-compose up` avec Airflow et Ollama. Un `curl localhost:8000/health` retourne 200 et montre DuckDB + Ollama en status ok.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Creer `Dockerfile.api` (base python:3.11-slim, install depuis pyproject.toml, copie src/)
- [ ] Renommer `Dockerfile` existant en `Dockerfile.airflow`
- [ ] Ajouter le service `api` dans `docker-compose.yaml` avec le volume `data/duckdb` partage, dependance `ollama`, variables d'environnement `IWF_DUCKDB_PATH` et `IWF_OLLAMA_URL`
- [ ] Verifier : `docker-compose up` + `curl localhost:8000/health` = 200