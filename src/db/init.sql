-- Initialisation de la base DuckDB pour IWF AI Hub
-- Installation et chargement de l'extension VSS (Vector Similarity Search)
INSTALL vss;
LOAD vss;

-- Requis pour créer un index HNSW sur une base DuckDB persistante (fichier).
-- Le réglage provient de l'extension vss, il doit donc suivre LOAD vss.
SET hnsw_enable_experimental_persistence = true;

-- Table de stockage des chunks réglementaires vectorisés (RAG).
-- Source de vérité du schéma : init.sql (ne pas recréer la table ailleurs).
CREATE TABLE IF NOT EXISTS chunks (
    id          UUID DEFAULT gen_random_uuid(),
    source      VARCHAR NOT NULL,    -- nom du PDF
    article     VARCHAR,             -- numéro d'article IWF
    page        INTEGER,
    chunk_text  TEXT NOT NULL,
    embedding   FLOAT[768],          -- dimension du modèle Ollama nomic-embed-text
    created_at  TIMESTAMP DEFAULT now()
);

-- Index HNSW pour la recherche vectorielle par similarité cosinus.
-- ATTENTION : l'index HNSW ne persiste pas entre les sessions DuckDB.
-- Il doit être rechargé (recréé) au démarrage de l'application.
CREATE INDEX IF NOT EXISTS idx_chunks ON chunks
    USING HNSW (embedding)
    WITH (metric = 'cosine', ef_construction = 200, M = 16);
