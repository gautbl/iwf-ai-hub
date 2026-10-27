# Plan de ship — IWF AI Hub v1.0.0-alpha.1

## Décisions

| # | Question | Décision |
|---|---|---|
| 1 | Périmètre K8s | Allégé — **skippé pour le ship**. Réévaluation après client. |
| 2 | Priorité | **Polish client d'abord**, K8s plus tard. |
| 3 | Interface client | **Mini UI HTML** servie par FastAPI. |
| 4 | GLOSSARY + ADR | **Après le plan**, reflet des décisions. |
| 5 | Étendue mini UI | Page HTML statique (option A). |
| 6 | Données démo | **Données IWF réelles publiques** (PDFs + résultats). |
| 7 | Points douloureux | Les 3 résolus : VSS persist, seed embeddings, base de test. |
| 8 | Docker API | **Dockerisé maintenant** — un seul `docker-compose up`. |
| 9 | Ordre | **Séquentiel** — pas de parallélisation. |
| 10 | Version | **v1.0.0-alpha.1** |
| 11 | Client final | **Entraîneur + analyste** — les deux usages. |

## Tâches (ordre séquentiel)

### 1. Dockeriser l'API FastAPI

**Objectif** : L'API tourne dans `docker-compose up` avec Airflow, Ollama, DuckDB.

**Sous-tâches** :
- Nouveau Dockerfile pour l'API (`Dockerfile.api`) — basé python:3.11-slim.
- Ajout du service `api` dans `docker-compose.yaml`.
- Service `api` dépend de `ollama` et du volume DuckDB.
- Volume partagé `data/duckdb` monté dans le service API.
- Test : `docker-compose up` + `curl localhost:8000/health` = ok.

**Fichiers à créer/modifier** :
- `Dockerfile.api` (nouveau)
- `docker-compose.yaml` (ajout service api)

### 2. Script de seed et startup

**Objectif** : Un script `scripts/startup.sh` qui vérifie et initialise l'environnement.

**Sous-tâches** :
- `scripts/seed_demo.sh` — télécharge PDF IWF + CSV résultats publics.
- `scripts/startup.sh` — vérifie base, rebuild index VSS, pull modèles Ollama manquants.
- Lancement des embeddings pour les chunks PDF.
- Fix : VSS index rebuild au démarrage (via script ou init de l'app).
- Fix : seed de base de test retiré de git, fixture pytest recrée la base.

**Fichiers à créer/modifier** :
- `scripts/seed_demo.sh` (nouveau)
- `scripts/startup.sh` (nouveau)
- `src/db/init.sql` (éventuelle mise à jour)
- `.gitignore` (ajout `test_iwf_hub.duckdb`)

### 3. Mini UI Chat (page HTML)

**Objectif** : Une page HTML statique servie par FastAPI à l'URL racine `/`.

**Sous-tâches** :
- Page unique : champ texte, bouton envoyer, zone de réponse.
- Appel `POST /chat` via fetch JS.
- Design sobre, responsive, utilisable sur mobile.
- Montre le session_id pour suivre la conversation.

**Fichiers à créer** :
- `src/api/static/index.html` (ou intégré dans FastAPI)

### 4. Documentation domaine

**Objectif** : GLOSSARY.md + ADR clés pour le projet.

**Sous-tâches** :
- `GLOSSARY.md` — termes du domaine IWF (athlète, compétition, réglementation, résultat, session, etc.).
- `docs/adr/0001-architecture-souveraine.md` — pourquoi tout est local, pas de cloud.
- `docs/adr/0002-duckdb-vss-pour-rag.md` — pourquoi DuckDB VSS plutôt qu'une base vectorielle dédiée.

### 5. Polish README et tag

**Objectif** : README à jour pour un nouveau développeur ou client.

**Sous-tâches** :
- README mis à jour avec instructions one-click `docker-compose up`.
- Section "Démo client" avec URL et usage.
- Tag `v1.0.0-alpha.1`.
- CHANGELOG.md ou release notes.

## Tests de validation

- `pytest tests/` — 81 tests verts.
- `docker-compose up` + `curl localhost:8000/health` = ok.
- `curl localhost:8000/` = page HTML chat.
- `curl -X POST localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"Quelles sont les règles antidopage?"}'` = réponse.