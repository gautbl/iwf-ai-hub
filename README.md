# IWF AI Hub

Plateforme d'intelligence augmentée pour l'International Weightlifting Federation (IWF).

## Arborescence

iwf-ai-hub/
├── .git/
├── .gitignore
├── README.md
├── docker-compose.yaml
├── data/
│   ├── pdfs/
│   └── duckdb/
├── src/
│   └── db/
│       └── init.sql
└── requirements/
    └── base.txt

## Architecture
- **Orchestration** : LangGraph
- **Base de données hybride** : DuckDB (SQL & VSS)
- **LLM & Embeddings** : Ollama (Local)
- **Pipelines** : Apache Airflow
- **API** : FastAPI

## Quick Start
1. `git clone <url-de-votre-repo>`
2. `docker-compose up -d`
