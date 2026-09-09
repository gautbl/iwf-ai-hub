# IWF AI Hub

Plateforme d'intelligence augmentée pour l'International Weightlifting Federation (IWF).
Architecture moderne de Data + IA, migrée de Docker Compose vers Kubernetes pour la scalabilité
et la souveraineté des données.

---

## 🎯 Problème métier

L'IWF gère un volume croissant de données (résultats de compétitions, réglementations anti-dopage,
historiques athlètes) réparties dans des PDFs non structurés et des bases de données hétérogènes.

**Objectifs :**
- Centraliser et structurer les données IWF (ETL moderne)
- Permettre l'interrogation en langage naturel des réglementations (RAG)
- Fournir un agent IA conversationnel pour les analystes et entraîneurs
- Garantir la souveraineté des données (infrastructure on-premise / cloud souverain)

---

## 🏗️ Architecture

```mermaid
graph TB

    subgraph DataSources["📥 Sources de données"]
        PDF[📄 PDFs Réglementations IWF]
        CSV[📊 CSV Résultats compétitions]
        API_EXT[🌐 APIs externes IWF]
    end

    subgraph Ingestion["🔄 Ingestion & ETL"]
        AIRFLOW[Apache Airflow<br/>Orchestration]
        DBT[dbt<br/>Transformation SQL]
    end

    subgraph Storage["🗄️ Stockage"]
        DUCKDB[(DuckDB<br/>SQL + Vectoriel VSS)]
        VSS[Extension VSS<br/>HNSW Index]
    end

    subgraph AI["🤖 Intelligence Artificielle"]
        OLLAMA[Ollama<br/>LLM Local]
        EMBED[Embeddings<br/>Modèle local]
        RAG[RAG Pipeline<br/>Retrieval + Génération]
        AGENT[Agent LangGraph<br/>Mémoire + Outils]
    end

    subgraph API["🌐 Exposition API"]
        FASTAPI[FastAPI<br/>REST Endpoints]
        AUTH[Auth X-API-Key]
        MONITOR[Prometheus<br/>Métriques]
    end

    subgraph K8s["☸️ Infrastructure Kubernetes"]
        NS[Namespace iwf-ai-hub]
        INGRESS[Ingress Controller]
        PV[Persistent Volumes<br/>DuckDB data]
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
    
    INGRESS --> FASTAPI
    PV --> DUCKDB
    
    style K8s fill:#e1f5fe
    style AI fill:#fff3e0
    style AIRFLOW fill:#e8f5e9
```

### 📖 Légende du diagramme d'architecture

#### Types de nœuds

Symbole | Type | Description |
|---|---|---|
| 📄 📊 🌐 | Sources de données | Documents non structurés (PDFs), fichiers CSV, APIs externes |
| 🔄 | Orchestration ETL | Apache Airflow pour le scheduling et dbt pour la transformation |
| 🗄️ | Stockage | DuckDB avec extension VSS pour SQL + recherche vectorielle |
| 🤖 | Intelligence Artificielle | Ollama (LLM local), embeddings, RAG et agent conversationnel |
| 🌐 | API & Sécurité | FastAPI pour l'exposition REST, authentification et monitoring |
| ☸️ | Infrastructure | Kubernetes pour l'orchestration des conteneurs en production |

#### Flux de données

Flèche | Signification |
|---|---|
| → | Flux de données : Déplacement ou transformation de données entre composants |
| CSV/PDF → Airflow | Ingestion des sources brutes vers l'orchestrateur |
| Airflow → dbt → DuckDB | Pipeline ETL : extraction, transformation, chargement |
| DuckDB → VSS → RAG | Recherche vectorielle pour alimenter le RAG |
| Ollama → Embeddings → VSS | Génération d'embeddings locaux et stockage |
| Agent → FastAPI | Exposition de l'agent IA via API REST |
| Ingress → FastAPI | Routage externe vers les services Kubernetes |

#### Couleurs (styles)

Couleur | Composant | Raison |
|---|---|---|
| 🟢 Vert clair | Airflow | Orchestration centrale du pipeline |
| 🟠 Orange | IA | Couche intelligence artificielle |
| 🔵 Bleu clair | Kubernetes | Infrastructure cloud-native |

---



## 🛠️ Stack Technique

| Composant | Technologie | Rôle | Environnement |
|---|---|---|---|
| Orchestration | Apache Airflow | DAGs ETL, scheduling | Docker / Kubernetes |
| Transformation | dbt + DuckDB | Modélisation Star Schema | Container (via Airflow) |
| Base de données | DuckDB + VSS | SQL + Vector Search | Container / K8s |
| LLM & Embeddings | Ollama | LLM local, souveraineté | Container / K8s |
| Agent IA | LangGraph | Workflow conversationnel | .venv |
| API | FastAPI | Exposition REST | Container / K8s |
| Conteneurisation | Docker + Compose | Dev local | Local |
| Orchestration | Kubernetes | Production, scalabilité | Minikube / Cluster |
| Packaging | Helm | Déploiement K8s | K8s |
| CI/CD | GitLab CI | Build, test, deploy | GitLab |
| Monitoring | Prometheus/Grafana | Observabilité | K8s |

---

## 📁 Structure du projet

```
iwf-ai-hub/
│
├── 📁 k8s/                             # ⭐ Phase 6 (planned) — Déploiement Kubernetes
│   ├── namespace.yaml                   # Isolation iwf-ai-hub
│   ├── configmap.yaml                   # Variables d'environnement
│   ├── secrets.yaml                     # Credentials (template)
│   ├── duckdb-statefulset.yaml          # Base de données persistante
│   ├── duckdb-service.yaml              # Service interne DuckDB
│   ├── ollama-deployment.yaml           # LLM local
│   ├── ollama-service.yaml
│   ├── airflow-deployment.yaml          # Orchestration
│   ├── api-deployment.yaml              # FastAPI
│   ├── api-service.yaml
│   └── ingress.yaml                     # Exposition externe
│
├── 📁 helm/                             # ⭐ Phase 6 (planned) — Packaging Helm
│   └── iwf-ai-hub/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│
├── 📁 .gitlab-ci.yml                    # ⭐ Phase 6 (planned) — CI/CD
│                                       
├── 📁 dags/                             # Airflow Workflows
│   ├── dag_etl_results.py               # Pipeline Bronze → Silver → Gold
│   └── dag_ingest_rules.py              # ⭐ Phase 3 — RAG pipeline (PDF download → chunk → embed)
│                                       
├── 📁 dbt/                              # Transformation Layer
│   ├── dbt_project.yml                  # Project config & materialization settings
│   ├── profiles.yml                     # DuckDB connection profile
│   └── models/                          # SQL transformation models
│       ├── sources.yml                  # External raw table declarations
│       ├── staging/                     # Silver Layer: Cleaning & Typing
│       │   └── stg_results.sql         
│       └── marts/                       # Gold Layer: Star Schema (BI Ready)
│           ├── dim_athletes.sql
│           ├── dim_weight_classes.sql
│           ├── fct_results.sql
│           └── schema.yml               # Data Quality Tests (not_null, unique, etc.)
│
├── 📁 src/                              # Source Code
│   ├── 📁 db/
│   │   └── init.sql                     # VSS Extension installation
│   ├── 📁 pipelines/
│   │   ├── extract_results.py           # Bronze Layer: Data Extraction
│   │   ├── load_pdfs.py                 # Chargement PDFs
│   │   ├── chunking.py                  # Découpage texte
│   │   ├── embeddings.py                # Vectorisation
│   │   └── retrieval.py                 # ⭐ Phase 3 (not yet created)
│   ├── 📁 agent/                        # ⭐ Phase 4 (not yet created)
│   │   └── ...
│   └── 📁 api/                          # ⭐ Phase 5 (not yet created)
│       └── ...
│
├── 📁 tests/                            # Tests unitaires & intégration
│   ├── conftest.py                      # pytest markers (network)
│   ├── test_etl.py
│   ├── test_etl_ow.py
│   └── test_rag.py
│
├── 📁 data/
│   ├── pdfs/                            # (empty — no IWF PDFs added yet)
│   └── duckdb/                          # Base de données (volume)
│
├── 📁 requirements/                     # Environnements isolés
│   ├── base.txt
│   └── airflow.txt
│
├── docker-compose.yaml                  # Dev local (Docker)
├── Dockerfile                           # Custom Airflow + dbt-duckdb
└── README.md                            # Ce fichier
```

---

## Architecture
- **Orchestration** : LangGraph
- **Base de données hybride** : DuckDB (SQL & VSS)
- **LLM & Embeddings** : Ollama (Local)
- **Pipelines** : Apache Airflow
- **API** : FastAPI

## 🚀 Quick Start
### Option 1 : Docker Compose (Développement local)
```bash
# 1. Cloner le repo
git clone https://github.com/gautbl/iwf-ai-hub.git
cd iwf-ai-hub

# 2. Lancer l'infrastructure
docker-compose up -d

# 3. Vérifier les services
curl http://localhost:8080/health  # Airflow
curl http://localhost:11434/api/tags  # Ollama
```

### Option 2 : Kubernetes — Phase 6 (planned)

Le déploiement Kubernetes sera disponible en Phase 6 avec les manifests `k8s/*.yaml` et le chart Helm `helm/iwf-ai-hub/`. En attendant, utilisez Docker Compose (Option 1) pour le développement local.

---

## 📋 Roadmap

Phase | Composant | Statut | Description |
|---|---|---|---|
| Phase 1 | Infrastructure Docker | ✅ Terminé | Airflow, DuckDB, Ollama |
| Phase 2 | Pipeline ETL | ✅ Terminé | dbt, Star Schema, tests |
| Phase 3 | Pipeline RAG | 🚧 En cours | PDFs, chunking, embeddings |
| Phase 4 | Agent LangGraph | ⏳ À venir | Outils, mémoire, workflow |
| Phase 5 | API FastAPI | ⏳ À venir | REST, auth, monitoring |
| Phase 6 | Kubernetes | ⏳ À venir | Migration, Helm, CI/CD |

---

## 🎯 Objectif Professionnel
Ce projet démontre une architecture IA/Data moderne et souveraine, alignée avec les enjeux
de confidentialité et de performance. La migration vers Kubernetes illustre la capacité à
industrialiser une solution IA pour la production à grande échelle.

### Compétences clés mises en avant :

Architecture de données (ETL, modélisation, qualité)
Intelligence artificielle (RAG, LLM local, agents)
DevOps & Infrastructure (Docker, Kubernetes, CI/CD)
Souveraineté des données (on-premise, open source)

---

## 🔗 Liens utiles
DuckDB VSS Extension: https://duckdb.org/docs/extensions/vss
LangGraph Documentation: https://langchain-ai.github.io/langgraph/
Ollama: https://ollama.ai
Kubernetes Documentation: https://kubernetes.io/docs/home/

---

## 📝 Licence
MIT — Projet personnel open source