## Question

Current coverage is 89% overall. Target: raise to ≥92% with meaningful tests for the untested paths, not just coverage padding.

Blocker: `01-align-deps` (pytest-cov and coverage tooling may need installation first).

The specific gaps:
- **`src/api/main.py` (77%)** — health check error paths (DuckDB connection failure, Ollama timeout → `degraded` status), chat edge cases (empty messages → 502, agent exception → 500)
- **`src/pipelines/extract_results.py` (71%)** — core ETL classes `DataExtractor`, `OpenWeightliftingExtractor`, `DataLoader` have low coverage and missing docstrings
- **`src/pipelines/retrieval.py` (80%)** — error handling on DuckDB/Ollama failure
- **`src/agent/tools.py` (91%)** — DB connection error paths in `query_results` and `compute_athlete_stats`
- **`src/api/dependencies.py` (86%)** — line 34 `get_agent_app` error path

For each gap, add tests that verify the degraded behaviour (e.g., when DuckDB is unreachable, the tool returns `[]` not a crash) and the happy path when dependencies work.

Type: task
Status: open
Blocked by: 01