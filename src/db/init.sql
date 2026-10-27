-- Initialises the DuckDB database for IWF AI Hub
-- Install and load the VSS extension (Vector Similarity Search)
INSTALL vss;
LOAD vss;

-- Needed to build an HNSW index on a persistent DuckDB file.
-- This setting comes from the vss extension, so it must follow LOAD vss.
SET hnsw_enable_experimental_persistence = true;

-- Table for storing vectorised regulation chunks (RAG).
-- Schema source of truth: init.sql. Do not recreate the table elsewhere.
CREATE TABLE IF NOT EXISTS chunks (
    id          UUID DEFAULT gen_random_uuid(),
    source      VARCHAR NOT NULL,    -- PDF file name
    article     VARCHAR,             -- IWF article number
    page        INTEGER,
    chunk_text  TEXT NOT NULL,
    embedding   FLOAT[768],          -- dimension of the Ollama nomic-embed-text model
    created_at  TIMESTAMP DEFAULT now()
);

-- HNSW index for vector similarity search (cosine).
-- WARNING: the HNSW index does not persist across DuckDB sessions.
-- It must be rebuilt on application startup.
CREATE INDEX IF NOT EXISTS idx_chunks ON chunks
    USING HNSW (embedding)
    WITH (metric = 'cosine', ef_construction = 200, M = 16);