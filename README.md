# IWF AI Hub

Plateforme d'IA pour l'International Weightlifting Federation (IWF).
Architecture Data + IA avec Docker Compose pour la scalabilité
et la souveraineté des données.

---

## Problème métier

L'IWF gère un volume croissant de données (résultats de compétitions, réglementations anti-dopage,
historiques athlètes) dans des PDFs et bases de données hétérogènes.

**Objectifs :**
- Centraliser et structurer les données IWF (ETL moderne)
- Permettre l'interrogation en langage naturel des réglementations (RAG)
- Fournir un agent IA conversationnel pour les analystes et entraîneurs
- Garantir la souveraineté des données (infrastructure on-premise / cloud souverain)

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

## Stack Technique

| Composant | Technologie | Role | Environnement |
|---|---|---|---|
| Orchestration | Apache Airflow | DAGs ETL, scheduling | Docker |
| Transformation | dbt + DuckDB | Star Schema | Container (via Airflow) |
| Traitement distribue | PySpark | Miroir Silver (Phase 2.5) | Docker / venv dedie |
| Base de donnees | DuckDB + VSS | SQL + Vector Search | Container |
| LLM and Embeddings | Ollama | LLM local, souverainete | Container |
| Agent IA | LangGraph | Workflow conversationnel | .venv |
| API | FastAPI | Exposition REST | .venv / Container |
| Conteneurisation | Docker + Compose | Dev local | Local |
| Monitoring | Prometheus/Grafana | Observabilite | Docker |

---

## Structure du projet

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

> **Note DuckDB VSS** : La creation d'un index HNSW exige
> `SET hnsw_enable_experimental_persistence = true;` apres `LOAD vss;`
> (dans `src/db/init.sql`).
> L'index HNSW ne persiste pas entre les sessions DuckDB.

> **Sources PDF IWF** : URL dans `dags/dag_ingest_rules.py` :
> `https://www.iwf.net/wp-content/uploads/downloads/2024/01/IWF_TCRR_2024.pdf`

## Quick Start

### Pre-requis

- Python 3.11+
- DuckDB (extension VSS activee)
- Ollama avec les modeles `nomic-embed-text` et `llama3.2`
- Docker et Docker Compose (pour l'ETL Airflow)

### Option 1 : Docker Compose (developpement local)

```bash
git clone https://github.com/gautbl/iwf-ai-hub.git
cd iwf-ai-hub
docker-compose up -d
curl http://localhost:8080/health
curl http://localhost:11434/api/tags
```

### Option 2 : API FastAPI (developpement local)

```bash
.venv\Scripts\activate  # Windows
uvicorn src.api.main:app --reload
curl http://localhost:8000/health
```

L'API expose deux endpoints :
- `GET /health` : etat de sante (DuckDB, Ollama)
- `POST /chat` : conversation avec l'agent IWF

---

## Roadmap

Phase | Composant | Statut | Description |
|---|---|---|---|
| Phase 1 | Infrastructure Docker | Fait | Airflow, DuckDB, Ollama |
| Phase 2 | Pipeline ETL | Fait | dbt, Star Schema, tests |
| Phase 3 | Pipeline RAG | Fait | PDFs, chunking, embeddings, retrieval |
| Phase 4 | Agent LangGraph | Fait | Outils, memoire, workflow |
| Phase 5 | API FastAPI | Fait | REST, auth, monitoring |
| Phase 6 | Kubernetes | A venir | Migration, Helm, CI/CD |
| Phase 2.5 | Miroir PySpark Silver | Optionnel | Transformation + validation parite |
| Phase 7 | Couche d'ingestion | Optionnel | MinIO + boto3 |

---

## Licence
MIT - Projet personnel open source