---
description: RAG pipeline - chunking, embeddings, vector retrieval on DuckDB VSS
model: opencode-go/deepseek-v4-flash
permission:
  edit: ask
  bash: ask
---

You implement phase 3 of iwf-ai-hub.

## Scope
- src/pipelines/chunking.py    (to create)
- src/pipelines/embeddings.py  (to create)
- src/pipelines/retrieval.py   (to create)
- src/pipelines/load_pdfs.py   (to extend)
- tests/test_rag.py

## Hard constraints
- Embeddings via local Ollama only (http://localhost:11434)
  Never use a remote embeddings API
- Vector storage: DuckDB VSS extension (HNSW)
  Database file: data/duckdb/iwf_hub.duckdb
- Python environment: .venv exclusively

## Test format
- Use reportlab for test PDFs (already used in the project)
- One test per public function
- Always clean up temporary files (conftest.py or teardown)

## Chunking for IWF regulatory documents
- Split by article or logical section, not by fixed token count
- Preserve metadata: source, article number, page

## Language
Documentation and docstrings in French, variable names in English.