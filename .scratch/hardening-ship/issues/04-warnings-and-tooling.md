## Question

Two issues in one ticket because they're connected:

**A. Deprecation warnings (2 currently):**
- `LangChainPendingDeprecationWarning` in langgraph — `allowed_objects` default will change. Fix: pass `allowed_objects='core'` explicitly where langgraph checkpoint is initialized.
- `DeprecationWarning` in anyio — `BlockingPortal` alias. This comes from starlette testclient and needs `httpx2` installed to resolve (starlette 1.6.0 expects `httpx2`). Fix: install `httpx2` and migrate test imports.

After both fixes, verify `pytest -W error tests/` passes cleanly.

**B. Dev tooling:**
- `mypy`, `ruff`, `black`, `pre-commit` listed in `pyproject.toml [dev]` but not installed in `.venv`
- Decision: install them and run once to get baseline clean. If clean requires significant refactoring, defer the clean to a later ticket — this ticket is about having the tools available and documenting their config.

Blocker: `01-align-deps` (tooling list may change based on dep decisions).

Type: task
Status: open
Blocked by: 01