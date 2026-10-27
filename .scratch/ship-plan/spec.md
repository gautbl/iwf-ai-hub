Status: ready-for-agent

## Problem Statement

The IWF AI Hub has 81 green tests and a complete pipeline. But it has no client interface, no one-click startup, and the API runs in a host venv. A client cannot try the product without starting two processes. The demo is not ready.

## Solution

A one-click startup with `docker-compose up` that starts the API, Ollama and Airflow. An HTML chat page served by the API at root `/`. Seed scripts that download public IWF data. All tagged `v1.0.0-alpha.1`.

## User Stories

1. As an IWF client, I want a single `docker-compose up` to see the product work, so I do not need to know the internal architecture.

2. As an IWF client, I want a chat page at `http://localhost:8000`, to ask questions without a technical tool.

3. As a coach, I want to ask questions about IWF regulations via the chat, to get sourced answers quickly.

4. As an analyst, I want to query competition results via the chat, to analyse performance without SQL.

5. As a client, I want the conversation to persist across messages, to ask follow-up questions.

6. As a client, I want to see real IWF data, to validate the product.

7. As a client, I want Ollama models to download automatically, so I do not install them manually.

8. As a developer, I want demo data to seed automatically.

9. As a developer, I want an up-to-date README with one-click instructions.

10. As a client, I want the VSS index to rebuild automatically, so the RAG responds immediately.

11. As a developer, I want the test DB to be recreated by pytest, so a binary is not versioned.

## Implementation Decisions

### 1. Dockerise the FastAPI API

A new Dockerfile (`Dockerfile.api`) based on `python:3.11-slim` installs dependencies from `pyproject.toml`. It then copies the source code `src/`.

The `api` service is added to `docker-compose.yaml`. It shares the `data/duckdb` volume with the `airflow` service. It depends on `ollama`. Environment variables are passed via the `environment:` block.

Port 8000 is exposed. The entry point is `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`.

The existing Airflow Dockerfile (`Dockerfile`) is renamed `Dockerfile.airflow`. The `airflow` service points to `dockerfile: Dockerfile.airflow`.

### 2. Seed and startup scripts

Two shell scripts in `scripts/` :

**`scripts/seed_demo.sh`** :
- Downloads IWF PDFs from the official site.
- Downloads result CSVs from OpenWeightlifting.
- Runs chunking and embeddings via Ollama.

**`scripts/startup.sh`** :
- Checks that `data/duckdb/` exists.
- Checks Ollama models and pulls them if absent.
- Rebuilds the HNSW VSS index on the `chunks` table.

The startup script is idempotent. It runs on container startup.

### 3. HTML chat page

A single page `src/api/static/index.html` served by FastAPI at root `/` via a `GET /` route.

Features :
- Text input for the question.
- "Send" button.
- Response area that shows the agent text.
- Display of the current `session_id`.
- Calls `POST /chat` via `fetch()`.
- Clean and responsive design.

The designer agent will be consulted for the visual rendering.

### 4. GLOSSARY.md and ADR

**`GLOSSARY.md`** — IWF domain glossary :
- **Athlete** : a person registered for a competition.
- **Competition** : an IWF event with athletes.
- **Result** : an athlete performance.
- **Regulation** : a PDF document with IWF rules.
- **Session** : a single conversation with the agent.
- **Chunk** : a vectorised text segment for the RAG.

**`docs/adr/0001-sovereign-architecture.md`** — why everything is local :
- Context: sovereignty of IWF data, no cloud.
- Decision: local Ollama, DuckDB file, no managed service.
- Rejected alternatives: OpenAI, Pinecone, BigQuery.

**`docs/adr/0002-duckdb-vss-for-rag.md`** — why DuckDB VSS :
- Context: need for vector search without new infrastructure.
- Decision: DuckDB VSS extension.
- Trade-off: the index does not persist across sessions.

### 5. README and tag

README updated :
- `docker-compose up` instructions.
- "Client demo" section with URL and examples.
- Endpoint table (GET /health, POST /chat, GET /).
- Tag `v1.0.0-alpha.1` after validation.

The file `test_iwf_hub.duckdb` is added to `.gitignore`.

### Seams de test

Existing tests cover the API (TestClient), the agent (mock LLM), and the RAG (mock Ollama). No new seam is needed :

- API tests: 27 tests in `test_api.py`. The `GET /` route will be tested with the same TestClient.
- Container tests: optional, not included.
- Seed tests: no unit test for shell scripts.

## Testing Decisions

### What makes a good test
- Test external behaviour, not the implementation.
- Do not make network calls in unit tests.
- Use existing seams.
- One test per scenario.

### Modules tested

| Module | Existing tests | New tests |
|---|---|---|
| `src/api/main.py` | `test_api.py` | `GET /` = 200 + HTML |
| `scripts/startup.sh` | none | no test |

### New tests

1. `test_chat_serves_html_at_root` — `GET /` = 200 with `text/html`, contains "IWF".
2. `test_chat_html_includes_form` — the HTML has an `<input>` for the question and a button.

## Out of Scope

- **Kubernetes, Helm, CI/CD** : re-evaluate after client.
- **PySpark mirror** : optional.
- **MinIO / bronze ingestion** : optional.
- **Front-end React or Streamlit** : static HTML page is enough.
- **Docker integration tests** : need real Ollama.
- **Authentication** : no login in alpha.

## Further Notes

- Sequential execution: Dockerisation, Seed, UI, GLOSSARY+ADR, README+tag.
- The `Dockerfile` file is renamed `Dockerfile.airflow`.
- Embeddings are stored in the `chunks` table with HNSW index recreated each session.