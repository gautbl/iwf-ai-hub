## Question

After code hardening, update the project documentation to reflect reality:

- **README.md**: 
  - Mark Phases 4 and 5 as ✅ Done (not ⏳ Coming)
  - Update the file tree — `src/agent/` and `src/api/` exist, fix their "(not yet created)" annotations
  - Add a section on running the API locally (`uvicorn src.api.main:app`)
  - Add a `.env.example` file documenting `IWF_*` env vars (matching `src/api/config.py`)
  - Remove outdated K8s/Helm references from the file tree since they're deferred
  - Add a "Prerequisites" block mentioning Python 3.11, DuckDB, Ollama

- **AGENTS.md**:
  - Update "Current Status" to reflect Phases 4-5 done, Phase 6 deferred
  - Remove K8s/Helm/CI items from "Known Issues"
  - Add Python version (3.11.9) to the environment section

- **`.env.example`**: Create from `src/api/config.py` fields (IWF_HOST, IWF_PORT, IWF_LOG_LEVEL, IWF_DUCKDB_PATH, IWF_OLLAMA_URL, IWF_LLM_MODEL) with local-dev defaults

Blocker: all prior tickets (docs should reflect the hardened state, not the pre-hardening state).

Type: task
Status: open
Blocked by: 01, 02, 03, 04