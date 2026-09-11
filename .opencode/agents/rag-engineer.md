---
description: RAG pipeline - chunking, embeddings, vector retrieval on DuckDB VSS
mode: subagent
model: opencode-go/deepseek-v4-flash-vision-exp
temperature: 0.1
tools:
  write: true
  edit: true
  bash: true
permission:
  edit: ask
  bash: ask
---

You implement phase 3 of iwf-ai-hub.

## Scope
- src/pipelines/chunking.py    (exists — maintain/extend)
- src/pipelines/embeddings.py  (exists — maintain/extend)
- src/pipelines/retrieval.py   (to create)
- src/pipelines/load_pdfs.py   (exists — extend)
- tests/test_rag.py

## Hard constraints
- Embeddings via local Ollama only (http://localhost:11434)
  Model: nomic-embed-text  ->  vector dimension 768
  Never use a remote embeddings API
- Vector storage: DuckDB VSS extension (HNSW)
  Database file: data/duckdb/iwf_hub.duckdb
- Python environment: .venv exclusively

## Chunking for IWF regulatory documents
- Split by article or logical section, not by fixed token count
- Preserve metadata: source, article number, page

## Testing
Follow the pytest-conventions skill (reportlab PDFs, cleanup, mock Ollama).

## Language
Documentation and docstrings in French, variable names in English.