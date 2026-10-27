Status: ready-for-agent

## Problem Statement

L'IWF AI Hub a 81 tests verts et un pipeline complet. Mais il n'a pas d'interface client, pas de demarrage one-click, et l'API tourne dans un venv hote. Un client ne peut pas essayer le produit sans lancer deux processus. La demo n'est pas prete.

## Solution

Un demarrage one-click avec `docker-compose up` qui lance l'API, Ollama et Airflow. Une page de chat HTML servie par l'API a la racine `/`. Des scripts de seed qui telechargent les donnees IWF publiques. Le tout tague `v1.0.0-alpha.1`.

## User Stories

1. En tant que client IWF, je veux un seul `docker-compose up` pour voir le produit fonctionner, pour ne pas connaitre l'architecture interne.

2. En tant que client IWF, je veux une page de chat a `http://localhost:8000`, pour poser des questions sans outil technique.

3. En tant qu'entraineur, je veux poser des questions sur les reglementations IWF via le chat, pour obtenir des reponses sourcees rapidement.

4. En tant qu'analyste, je veux interroger les resultats de competition via le chat, pour analyser les performances sans SQL.

5. En tant que client, je veux que la conversation persiste entre les messages, pour poser des questions de suivi.

6. En tant que client, je veux voir les donnees reelles de l'IWF, pour valider le produit.

7. En tant que client, je veux que les modeles Ollama soient telecharges automatiquement, pour ne pas les installer manuellement.

8. En tant que developpeur, je veux que les donnees de demo soient seedees automatiquement.

9. En tant que developpeur, je veux un README a jour avec les instructions one-click.

10. En tant que client, je veux que l'index VSS se reconstruise automatiquement, pour que le RAG reponde immediatement.

11. En tant que developpeur, je veux que la base de test soit recreee par pytest, pour ne pas versionner un binaire.

## Implementation Decisions

### 1. Dockerisation de l'API FastAPI

Un nouveau Dockerfile (`Dockerfile.api`) base sur `python:3.11-slim` installe les dependances depuis `pyproject.toml`. Il copie ensuite le code source `src/`.

Le service `api` est ajoute a `docker-compose.yaml`. Il partage le volume `data/duckdb` avec le service `airflow`. Il depend de `ollama`. Les variables d'environnement sont passees via le bloc `environment:`.

Le port 8000 est expose. Le point d'entree est `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`.

Le Dockerfile Airflow existant (`Dockerfile`) est renomme `Dockerfile.airflow`. Le service `airflow` pointe vers `dockerfile: Dockerfile.airflow`.

### 2. Scripts de seed et startup

Deux scripts shell dans `scripts/` :

**`scripts/seed_demo.sh`** :
- Telecharge les PDF IWF depuis le site officiel.
- Telecharge les CSV de resultats depuis OpenWeightlifting.
- Lance le chunking et les embeddings via Ollama.

**`scripts/startup.sh`** :
- Verifie que `data/duckdb/` existe.
- Verifie les modeles Ollama et les pull si absents.
- Reconstruit l'index HNSW VSS sur la table `chunks`.

Le script de startup est idempotent. Il s'execute au demarrage du conteneur.

### 3. Page HTML de chat

Une page unique `src/api/static/index.html` servie par FastAPI a la racine `/` via une route `GET /`.

Fonctionnalites :
- Champ de saisie pour la question.
- Bouton "Envoyer".
- Zone de reponse qui affiche le texte de l'agent.
- Affichage du `session_id` courant.
- Appels `POST /chat` via `fetch()`.
- Design sobre et responsive.

Le designer agent sera consulte pour le rendu visuel.

### 4. GLOSSARY.md et ADR

**`GLOSSARY.md`** — glossaire du domaine IWF :
- **Athlete** : personne inscrite a une competition.
- **Competition** : evenement IWF avec des athletes.
- **Resultat** : performance d'un athlete.
- **Reglementation** : document PDF avec les regles IWF.
- **Session** : conversation unique avec l'agent.
- **Chunk** : extrait de texte vectorise pour le RAG.

**`docs/adr/0001-architecture-souveraine.md`** — pourquoi tout est local :
- Contexte : souverainete des donnees IWF, pas de cloud.
- Decision : Ollama local, DuckDB fichier, aucun service managed.
- Alternatives rejetees : OpenAI, Pinecone, BigQuery.

**`docs/adr/0002-duckdb-vss-pour-rag.md`** — pourquoi DuckDB VSS :
- Contexte : besoin de recherche vectorielle sans nouvelle infra.
- Decision : extension VSS de DuckDB.
- Trade-off : l'index ne persiste pas entre sessions.

### 5. README et tag

README mis a jour :
- Instructions `docker-compose up`.
- Section "Demo client" avec URL et exemples.
- Tableau des endpoints (GET /health, POST /chat, GET /).
- Tag `v1.0.0-alpha.1` apres validation.

Le fichier `test_iwf_hub.duckdb` est ajoute a `.gitignore`.

### Seams de test

Les tests existants couvrent l'API (TestClient), l'agent (mock LLM), et le RAG (mock Ollama). Aucune nouvelle seam n'est necessaire :

- Tests API : 27 tests dans `test_api.py`. La route `GET /` sera testee avec le meme TestClient.
- Tests conteneur : optionnel, pas inclus.
- Tests seed : pas de test unitaire pour les scripts shell.

## Testing Decisions

### Ce qui fait un bon test
- Tester le comportement externe, pas l'implementation.
- Ne pas faire d'appels reseau en tests unitaires.
- Utiliser les seams existantes.
- Un test par scenario.

### Modules testees

| Module | Prior art | Nouveaux tests |
|---|---|---|
| `src/api/main.py` | `test_api.py` | `GET /` = 200 + HTML |
| `scripts/startup.sh` | aucun | pas de test |

### Nouveaux tests

1. `test_chat_serves_html_at_root` — `GET /` = 200 avec `text/html`, contient "IWF".
2. `test_chat_html_includes_form` — le HTML a un `<input>` pour la question et un bouton.

## Out of Scope

- **Kubernetes, Helm, CI/CD** : reevalue apres client.
- **PySpark mirror** : optionnel.
- **MinIO / ingestion bronze** : optionnel.
- **Front-end React ou Streamlit** : page HTML statique suffit.
- **Tests d'integration Docker** : besoin d'Ollama reel.
- **Authentification** : pas de login en alpha.

## Further Notes

- Execution sequentielle : Dockerisation, Seed, UI, GLOSSARY+ADR, README+tag.
- Le fichier `Dockerfile` est renomme `Dockerfile.airflow`.
- Les embeddings sont stockes dans la table `chunks` avec index HNSW recree a chaque session.
