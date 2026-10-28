# IWF AI Hub

AI platform for the International Weightlifting Federation (IWF).
Data + AI architecture with Docker Compose for scalability
and data sovereignty.

---

## Business problem

The IWF manages a growing volume of data (competition results, anti-doping regulations,
athlete history) across PDFs and heterogeneous databases.

**Goals :**
- Centralize and structure IWF data (modern ETL)
- Enable natural language query of regulations (RAG)
- Provide a conversational AI agent for analysts and coaches
- Guarantee data sovereignty (on-premise / sovereign cloud infrastructure)

---

## Architecture

```mermaid
graph TB

    subgraph DataSources["Sources de donnees"]
        PDF[PDFs Reglementations IWF]
        CSV[CSV Resultats competitions]
        API_EXT[APIs externes IWF]
    end

    subgraph Ingestion["Ingestion and ETL"]
        AIRFLOW[Apache Airflow]
        DBT[dbt]
    end

    subgraph Storage["Stockage"]
        DUCKDB[DuckDB SQL + VSS]
        VSS[Extension VSS HNSW]
    end

    subgraph AI["Intelligence Artificielle"]
        OLLAMA[Ollama LLM Local]
        EMBED[Embeddings]
        RAG[RAG Pipeline]
        AGENT[Agent LangGraph]
    end

    subgraph API["Exposition API"]
        FASTAPI[FastAPI REST]
        AUTH[Auth X-API-Key]
        MONITOR[Prometheus Metriques]
    end

    CSV --> AIRFLOW
    PDF --> AIRFLOW
    AIRFLOW --> DBT
    DBT --> DUCKDB

    DUCKDB --> VSS
    VSS --> RAG
    OLLAMA --> EMBED
    EMBED --> VSS
    RAG --> AGENT

    AGENT --> FASTAPI
    FASTAPI --> AUTH
    FASTAPI --> MONITOR
```

---

## Technical Stack

| Component | Technology | Role | Environment |
|---|---|---|---|
| Orchestration | Apache Airflow | ETL DAGs, scheduling | Docker |
| Transformation | dbt + DuckDB | Star Schema | Container (via Airflow) |
| Distributed processing | PySpark | Silver mirror (Phase 2.5) | Docker / dedicated venv |
| Database | DuckDB + VSS | SQL + Vector Search | Container |
| LLM and Embeddings | Ollama | Local LLM, data sovereignty | Container |
| AI Agent | LangGraph | Conversational workflow | .venv |
| API | FastAPI | REST exposure | .venv / Container |
| Containerisation | Docker + Compose | Local dev | Local |
| Monitoring | Prometheus/Grafana | Observability | Docker |

---

## Project structure

```
iwf-ai-hub/
│
├── dags/                             # Airflow Workflows
│   ├── dag_etl_results.py
│   └── dag_ingest_rules.py
│
├── dbt/                              # Transformation Layer
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── sources.yml
│       ├── staging/
│       │   └── stg_results.sql
│       └── marts/
│           ├── dim_athletes.sql
│           ├── dim_weight_classes.sql
│           ├── fct_results.sql
│           └── schema.yml
│
├── src/                              # Source Code
│   ├── db/
│   │   └── init.sql
│   ├── pipelines/
│   │   ├── extract_results.py
│   │   ├── load_pdfs.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   └── retrieval.py
│   ├── agent/                        # Phase 4 - Agent LangGraph
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── tools.py
│   └── api/                          # Phase 5 - API FastAPI
│       ├── config.py
│       ├── dependencies.py
│       ├── main.py
│       └── models.py
│
├── tests/
│   ├── conftest.py
│   ├── test_etl.py
│   ├── test_etl_ow.py
│   └── test_rag.py
│
├── notebooks/                         # Phase 2.5 (planned)
│   ├── silver_lifters.ipynb
│   └── validate_parity.ipynb
│
├── ingestion/                         # Phase 7 (planned)
│   ├── upload_bronze.py
│   └── README.md
│
├── data/
│   ├── pdfs/
│   └── duckdb/
│
├── requirements/
│   ├── base.txt
│   └── airflow.txt
│
├── .env.example
├── docker-compose.yaml
├── Dockerfile
└── README.md
```

---

> **DuckDB VSS note** : To build an HNSW index use
> `SET hnsw_enable_experimental_persistence = true;` after `LOAD vss;`
> (in `src/db/init.sql`).
> The HNSW index does not persist across DuckDB sessions.

> **Sources PDF IWF** : URL dans `dags/dag_ingest_rules.py` :
> `https://www.iwf.net/wp-content/uploads/downloads/2024/01/IWF_TCRR_2024.pdf`

## Quick Start

### Prerequisites

- Python 3.11+
- DuckDB (VSS extension enabled)
- Ollama with models `nomic-embed-text` and `llama3.2`
- Docker and Docker Compose (for the Airflow ETL)

### Option 1 : Docker Compose (local)

```bash
git clone https://github.com/gautbl/iwf-ai-hub.git
cd iwf-ai-hub
docker-compose up -d
curl http://localhost:8080/health
curl http://localhost:11434/api/tags
```

### Option 2 : FastAPI (local)

```bash
.venv\Scripts\activate  # Windows
uvicorn src.api.main:app --reload
curl http://localhost:8000/health
```

The API has two endpoints :
- `GET /health` : health check (DuckDB, Ollama)
- `POST /chat` : conversation with the IWF agent

> **Airflow build warning** : The Airflow container has a known NumPy version conflict
> (`numpy<2` required by some upstream dependencies) and pip dependency backtracking.
> The container still builds and runs successfully. If needed, track this at
> `.scratch/ship-plan/issues/06-harden-airflow-build.md`.

---

## Roadmap

Phase | Component | Status | Description |
|---|---|---|---|
| Phase 1 | Docker Infrastructure | Done | Airflow, DuckDB, Ollama |
| Phase 2 | ETL Pipeline | Done | dbt, Star Schema, tests |
| Phase 3 | RAG Pipeline | Done | PDFs, chunking, embeddings, retrieval |
| Phase 4 | LangGraph Agent | Done | Tools, memory, workflow |
| Phase 5 | FastAPI API | Done | REST, auth, monitoring |
| Phase 6 | Kubernetes | Coming | Migration, Helm, CI/CD |
| Phase 2.5 | PySpark Silver Mirror | Optional | Transformation + parity validation |
| Phase 7 | Ingestion Layer | Optional | MinIO + boto3 |

---

## TO-DO

 1. Pull models if needed: ollama pull nomic-embed-text and ollama pull llama3.2
 2. Run scripts/startup.sh — rebuilds the VSS index
 3. Launch the API: cd iwf-ai-hub && source .venv/bin/activate && uvicorn src.api.main:app --reload --port 8000
 4. Then curl localhost:8000/chat with a question
---

## License
MIT - Open source personal project
