## Question

The `pyproject.toml` has stale version pins that don't match the actual `.venv` installation (e.g. `duckdb==0.10.2` pinned but `1.5.5` installed, `pandas<2.2.0` but `3.0.5` installed, `numpy<2` but `2.4.6` installed). The `requirements/base.txt` is a different (slimmer) list with no pins at all. The installed deps work (58 tests pass) but the project metadata is actively misleading: anyone running `pip install -e .` gets untested versions.

## Decision

- `pyproject.toml` is the single source of truth for dependencies, with soft lower bounds matching the minimum tested versions.
- `requirements/base.txt` becomes a lockfile-style snapshot of `.venv` (pip freeze of runtime dependencies), with a commented header explaining its role.
- Missing dependencies were added: `pydantic`, `pydantic-settings`, `langchain-core`, `langchain-ollama`, `langgraph-checkpoint-duckdb` (previously transitive, now direct because imported).
- `numpy<2` removed (NumPy 2.x works with all current dependencies).
- `pandas<2.2.0` replaced with `pandas>=2.1`.
- `duckdb==0.10.2` replaced with `duckdb>=1.0`.
- `langchain>=0.1.0` replaced with `langchain-core>=1.0` + `langchain-ollama>=1.0` (only the packages actually used).
- `certifi` moved from `[dev]` to `[dev]` (test usage only).
- Dev dep bounds updated (black>=24, ruff>=0.5, mypy>=1.10, pre-commit>=3.7, reportlab>=4.0).
- Tests: 58 green unchanged.

Type: task
Status: resolved