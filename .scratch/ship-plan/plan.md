# Ship plan — IWF AI Hub v1.0.0-alpha.1

## Decisions

| # | Question | Decision |
|---|---|---|
| 1 | K8s scope | Reduced — **skipped for ship**. Re-evaluate after client. |
| 2 | Priority | **Client polish first**, K8s later. |
| 3 | Client interface | **Mini UI HTML** served by FastAPI. |
| 4 | GLOSSARY + ADR | **After the plan**, reflect decisions. |
| 5 | Mini UI scope | Static HTML page (option A). |
| 6 | Demo data | **Real public IWF data** (PDFs + results). |
| 7 | Pain points | All 3 resolved: VSS persist, seed embeddings, test DB. |
| 8 | Docker API | **Dockerised now** — single `docker-compose up`. |
| 9 | Order | **Sequential** — no parallelisation. |
| 10 | Version | **v1.0.0-alpha.1** |
| 11 | End client | **Coach + analyst** — both use cases. |

## Tasks (sequential order)

### 1. Dockerise the FastAPI API

**Goal** : The API runs in `docker-compose up` with Airflow, Ollama, DuckDB.

**Sub-tasks** :
- New Dockerfile for the API (`Dockerfile.api`) — based on python:3.11-slim.
- Add the `api` service to `docker-compose.yaml`.
- `api` service depends on `ollama` and the DuckDB volume.
- Shared volume `data/duckdb` mounted in the API service.
- Test: `docker-compose up` + `curl localhost:8000/health` = ok.

**Files to create or change** :
- `Dockerfile.api` (new)
- `docker-compose.yaml` (add api service)

### 2. Seed and startup script

**Goal** : A script `scripts/startup.sh` that checks and initialises the environment.

**Sub-tasks** :
- `scripts/seed_demo.sh` — downloads IWF PDF + public results CSV.
- `scripts/startup.sh` — checks DB, rebuilds VSS index, pulls missing Ollama models.
- Generate embeddings for PDF chunks.
- Fix: VSS index rebuild on startup (via script or app init).
- Fix: test DB seed removed from git, pytest fixture recreates the DB.

**Files to create or change** :
- `scripts/seed_demo.sh` (new)
- `scripts/startup.sh` (new)
- `src/db/init.sql` (possible update)
- `.gitignore` (add `test_iwf_hub.duckdb`)

### 3. Mini UI Chat (HTML page)

**Goal** : A static HTML page served by FastAPI at the root URL `/`.

**Sub-tasks** :
- Single page: text field, send button, response area.
- Call `POST /chat` via JS fetch.
- Clean, responsive design, usable on mobile.
- Show the session_id to follow the conversation.

**Files to create** :
- `src/api/static/index.html` (or integrated in FastAPI)

### 4. Domain documentation

**Goal** : GLOSSARY.md + key ADRs for the project.

**Sub-tasks** :
- `GLOSSARY.md` — IWF domain terms (athlete, competition, regulation, result, session, etc.).
- `docs/adr/0001-sovereign-architecture.md` — why everything is local, no cloud.
- `docs/adr/0002-duckdb-vss-for-rag.md` — why DuckDB VSS instead of a dedicated vector database.

### 5. Polish README and tag

**Goal** : README updated for a new developer or client.

**Sub-tasks** :
- README updated with one-click `docker-compose up` instructions.
- Section "Client demo" with URL and usage.
- Tag `v1.0.0-alpha.1`.
- CHANGELOG.md or release notes.

## Validation tests

- `pytest tests/` — 81 tests green.
- `docker-compose up` + `curl localhost:8000/health` = ok.
- `curl localhost:8000/` = HTML chat page.
- `curl -X POST localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"Quelles sont les règles antidopage?"}'` = response.