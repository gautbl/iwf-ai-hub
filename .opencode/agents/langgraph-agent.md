---
description: LangGraph conversational agent for IWF - phase 4
mode: subagent
model: opencode-go/deepseek-v4-flash
temperature: 0.2
tools:
  write: true
  edit: true
  bash: true
permission:
  edit: ask
  bash: ask
---

You implement phase 4 of iwf-ai-hub: the LangGraph conversational agent.

## Scope
- src/agent/__init__.py  (to create)
- src/agent/state.py     (to create) — AgentState definition
- src/agent/tools.py     (to create) — registered agent tools
- src/agent/graph.py     (to create) — main LangGraph graph
- tests/test_agent.py    (to create)

## Hard constraints
- LLM: ChatOllama, model llama3.2, http://localhost:11434 only
- Checkpointer: DuckDBSaver on data/duckdb/iwf_hub.duckdb
- Retrieval: calls src/pipelines/retrieval.py only, never a remote store
- Python environment: .venv exclusively

## Tools to implement (src/agent/tools.py)
- search_regulations(query: str, top_k: int = 5) -> list[dict]
    calls retrieval.retrieve(), returns relevant chunks

- query_results(
      athlete_name: str | None = None,
      category_name: str | None = None,
      event_date: str | None = None
  ) -> list[dict]
    SELECT on fct_results JOIN dim_athletes JOIN dim_weight_classes
    dynamic filters on non-null parameters

- compute_athlete_stats(athlete_name: str) -> dict
    aggregations: snatch max, clean_jerk max, total max, nb_competitions
    returns {} if athlete not found

## Testing
Follow pytest-conventions and langgraph-patterns skills:
- One unit test per node (mock LLM, mock retrieval)
- One graph-level integration test (mock LLM, real test_iwf_hub.duckdb)
- Never hit a live Ollama instance in unit tests

## Language
Docstrings and comments in French, variable names in English.