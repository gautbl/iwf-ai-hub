## Question

The `pyproject.toml` has stale version pins that don't match the actual `.venv` installation (e.g. `duckdb==0.10.2` pinned but `1.5.5` installed, `pandas<2.2.0` but `3.0.5` installed, `numpy<2` but `2.4.6` installed). The `requirements/base.txt` is a different (slimmer) list with no pins at all. The installed deps work (58 tests pass) but the project metadata is actively misleading: anyone running `pip install -e .` gets untested versions.

## Décision

- `pyproject.toml` est la source de vérité unique pour les dépendances, avec bornes inférieures souples correspondant aux versions minimales testées.
- `requirements/base.txt` devient un lockfile-style snapshot du `.venv` (pip freeze des dépendances runtime), avec un en-tête commenté qui explique son rôle.
- Les dépendances manquantes ont été ajoutées : `pydantic`, `pydantic-settings`, `langchain-core`, `langchain-ollama`, `langgraph-checkpoint-duckdb` (transitives auparavant, maintenant directes car importées).
- `numpy<2` supprimé (NumPy 2.x fonctionne avec toutes les dépendances actuelles).
- `pandas<2.2.0` remplacé par `pandas>=2.1`.
- `duckdb==0.10.2` remplacé par `duckdb>=1.0`.
- `langchain>=0.1.0` remplacé par `langchain-core>=1.0` + `langchain-ollama>=1.0` (seuls les sous-paquets réellement utilisés).
- `certifi` déplacé de `[dev]` vers `[dev]` (usage test uniquement). 
- Bornes des dev deps mises à jour (black>=24, ruff>=0.5, mypy>=1.10, pre-commit>=3.7, reportlab>=4.0).
- Tests : 58 verts inchangés.

Type: task
Status: resolved