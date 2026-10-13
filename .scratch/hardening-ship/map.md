# Map: Hardening & ship — IWF AI Hub

## Destination

Phases 1-5 of IWF AI Hub hardened (test coverage increased, deps aligned to reality, quality toolchain installed and clean) and documented (README/AGENTS.md accurate, `.env.example` present, warnings squashed) so the project is production-ready in its non-K8s form, with known gaps surfaced rather than hidden.

No K8s, no Helm, no CI/CD, no PySpark, no MinIO — those are deferred or optional.

## Notes

- **Domain**: Python 3.11, DuckDB, LangGraph, FastAPI, Ollama
- **Skills**: consulting `AGENTS.md` and existing conventions (structlog, pydantic-settings, pytest)
- **Language**: project comments/docs in French, code in English
- **Tests**: mocked Ollama throughout. Real end-to-end validation requires Docker + Ollama running — left as fog, not ticketed here.
- **Work**: This effort is about **hardening** (code quality, test coverage, dep alignment) then **documentation** (README, AGENTS.md, env setup). The dependency order is hardening → docs: don't document misleading deps before fixing them.

## Decisions so far

- **01-align-deps**: `pyproject.toml` est la source de vérité unique avec bornes inférieures souples. `requirements/base.txt` devient un lockfile-snapshot commenté. `numpy<2` supprimé, `pandas<2.2` remplacé, `duckdb==0.10.2` remplacé, `langchain` éclaté en `langchain-core` + `langchain-ollama`. Dependencies manquantes ajoutées (pydantic-settings, langchain-core, langchain-ollama, langgraph-checkpoint-duckdb). 58 tests verts.

- **04-warnings-and-tooling**: dev tooling installé (black, ruff, mypy, pre-commit) via `pip install -e .[dev]`. Configs ajoutées dans `pyproject.toml` : `[tool.ruff]`, `[tool.mypy]`, `[tool.black]`. Warnings amont (LangChainPendingDeprecationWarning, anyio DeprecationWarning) filtrées via pytest `filterwarnings`. `pytest -W error` passe : 81 tests, 0 erreurs. Patch de `LC_REVIVER` dans `src/agent/graph.py` avec `allowed_objects='core'` explicite.

## Not yet specified

- Real end-to-end smoke test (requires Docker + Ollama on this machine) — blocked on environment setup, not a code decision
- Whether the test database (`data/duckdb/test_iwf_hub.duckdb`) shipped in git is a problem — it's a binary artifact. May need a `.gitignore` entry and a fixture that creates it on demand.

## Out of scope

- Phase 6 (K8s, Helm, CI/CD) — deferred
- Phase 2.5 (PySpark mirror) — optional, after this effort
- Phase 7 (MinIO ingestion) — optional, after this effort
- Real Ollama integration test — environment-dependent, not a code decision