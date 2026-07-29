# IWF AI Hub

Plateforme d'intelligence augmentée pour l'International Weightlifting Federation (IWF).

## Arborescence

iwf-ai-hub/
├── .git/
├── .gitignore
├── README.md
├── docker-compose.yaml         # Orchestration (Airflow, Ollama, etc.)
├── Dockerfile                  # Custom image to include dbt-duckdb
├── dags/                        # Airflow Workflow Definitions
│   └── dag_etl_results.py      # Pipeline: Raw Extraction -> dbt Transform -> Test
├── data/                        # Data Volume (Mounted in Docker)
│   ├── pdfs/                    # IWF Regulation PDFs
│   └── duckdb/                  # Production DB (iwf_hub.duckdb)
├── dbt/                         # Transformation Layer
│   ├── dbt_project.yml          # Project config & materialization settings
│   ├── profiles.yml             # DuckDB connection profile
│   └── models/                  # SQL transformation models
│       ├── staging/             # Silver Layer: Cleaning & Typing
│       │   └── stg_results.sql
│       └── marts/               # Gold Layer: Star Schema (BI Ready)
│           ├── dim_athletes.sql
│           ├── dim_weight_classes.sql
│           ├── fct_results.sql
│           └── schema.yml       # Data Quality Tests (not_null, unique, etc.)
├── src/                         # Source Code
│   ├── db/
│   │   └── init.sql             # Infrastructure: VSS Extension installation
│   ├── pipelines/
│   │   └── extract_results.py   # Bronze Layer: Data Extraction
│   ├── agent/                  # AI Brain (Phase 4) -- NON CREE
│   │   ├── llm_config.py
│   │   ├── tools.py
│   │   └── graph.py
│   └── api/                    # API Layer (Phase 5) -- NON CREE
│       ├── main.py
│       └── models.py
├── requirements/               # Dependency Management
│   ├── base.txt
│   └── airflow.txt
└── tests/                       # Validation & Benchmarks -- NON CREE
    └── eval_ragas.py

## Architecture
- **Orchestration** : LangGraph
- **Base de données hybride** : DuckDB (SQL & VSS)
- **LLM & Embeddings** : Ollama (Local)
- **Pipelines** : Apache Airflow
- **API** : FastAPI

## Quick Start
1. `git clone <url-de-votre-repo>`
2. `docker-compose up -d`
