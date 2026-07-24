-- Installation et chargement de l'extension VSS (Vector Similarity Search)
INSTALL vss;
LOAD vss;

-- Table pour les données de performance
CREATE TABLE IF NOT EXISTS athletes (
    athlete_id INTEGER PRIMARY KEY,
    name VARCHAR,
    country VARCHAR,
    birth_year INTEGER
);

CREATE TABLE IF NOT EXISTS results (
    result_id INTEGER PRIMARY KEY,
    athlete_id INTEGER,
    competition_id INTEGER,
    total_weight DOUBLE,
    date DATE,
    FOREIGN KEY (athlete_id) REFERENCES athletes(athlete_id)
);

-- Table pour la partie RAG (Réglementation)
CREATE TABLE IF NOT EXISTS rules_embeddings (
    id INTEGER PRIMARY KEY,
    content TEXT,
    embedding FLOAT[384] -- Adapté à la dimension de paraphrase-multilingual-MiniLM-L12-v2
);
