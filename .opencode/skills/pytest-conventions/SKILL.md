---
name: pytest-conventions
description: Testing conventions for iwf-ai-hub - use before writing or reviewing any test
---

## General rules
- One test per public function (unit) plus one integration test per pipeline
- pytest only, no unittest.TestCase
- Strict types in test helpers, same as production code
- Logs via structlog, never print()

## Isolation and cleanup
- Always clean up temporary files (conftest.py fixture or teardown)
- Test DB: data/duckdb/test_iwf_hub.duckdb (auto-created and cleaned by tests)
- Never touch the production DB data/duckdb/iwf_hub.duckdb in tests

## Test data
- ETL tests fetch CSV from GitHub (network marker required)
  https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv
- SSL handled via certifi in test files
- RAG tests build temporary PDFs with reportlab

## Network marker
- Network-dependent tests carry the "network" marker (declared in conftest.py)
- Keep them separable so the suite can run offline where possible

## Mocking
- Mock the LLM and Ollama in unit tests; never hit a live Ollama instance
- Integration tests may target a real service only when explicitly intended

## Language
Docstrings and comments in French, variable names in English.