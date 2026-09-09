---
name: duckdb-vss
description: Using the DuckDB VSS extension for HNSW vector search
---

## Installation
```sql
INSTALL vss;
LOAD vss;
```

## Creating an HNSW index
```sql
CREATE INDEX idx_chunks ON chunks
  USING HNSW (embedding)
  WITH (metric = 'cosine', ef_construction = 200, M = 16);
```

## Critical pitfalls
- Vector dimension must match the Ollama embedding model exactly
- HNSW indexes do not persist across sessions: rebuild on startup
- Tune ef_search for the recall you need (default 40, up to 100)
- VSS requires DuckDB >= 0.10.0

## Search query
```sql
SELECT chunk_text, metadata, array_cosine_similarity(embedding, ?::FLOAT[768]) AS score
FROM chunks
ORDER BY score DESC
LIMIT 5;
```

## Recommended chunks table schema
```sql
CREATE TABLE chunks (
  id          UUID DEFAULT gen_random_uuid(),
  source      VARCHAR NOT NULL,    -- nom du PDF
  article     VARCHAR,             -- numéro d'article IWF
  page        INTEGER,
  chunk_text  TEXT NOT NULL,
  embedding   FLOAT[768],          -- adapter à la dimension du modèle Ollama
  created_at  TIMESTAMP DEFAULT now()
);
```