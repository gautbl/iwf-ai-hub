import os
from typing import Dict, List

import duckdb
import requests
import structlog

from src.pipelines.embeddings import EMBEDDING_DIM, EmbeddingGenerator

logger = structlog.get_logger()

# URL Ollama locale (surchargeable via variable d'environnement en conteneur).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"


def retrieve(query: str, db_path: str, top_k: int = 5) -> List[Dict]:
    """Recherche les chunks les plus proches de la requête dans DuckDB VSS.

    Args:
        query: question en langage naturel.
        db_path: chemin vers la base DuckDB contenant la table chunks.
        top_k: nombre maximum de résultats retournés.

    Returns:
        Liste de dicts {chunk_text, source, article, page, score} triés par
        score décroissant. Liste vide si Ollama est indisponible ou si la
        table chunks est vide.

    Raises:
        duckdb.Error: base DuckDB inaccessible ou requête invalide.
    """
    generator = EmbeddingGenerator(
        ollama_url=OLLAMA_URL, db_path=db_path, model_name=EMBEDDING_MODEL
    )

    try:
        query_vector = generator.embed_text(query)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.error("retrieve_ollama_unavailable", error=str(exc))
        return []

    conn = duckdb.connect(db_path)
    try:
        # L'index HNSW ne persiste pas entre les sessions DuckDB : on recharge
        # l'extension et on recrée l'index s'il est absent.
        conn.execute("INSTALL vss;")
        conn.execute("LOAD vss;")
        conn.execute("SET hnsw_enable_experimental_persistence = true;")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks ON chunks "
            "USING HNSW (embedding) "
            "WITH (metric = 'cosine', ef_construction = 200, M = 16);"
        )

        rows = conn.execute(
            f"""
            SELECT chunk_text, source, article, page,
                   array_cosine_similarity(embedding, ?::FLOAT[{EMBEDDING_DIM}]) AS score
            FROM chunks
            ORDER BY score DESC
            LIMIT ?
            """,
            [query_vector, top_k],
        ).fetchall()
    except duckdb.Error as exc:
        logger.error("retrieve_duckdb_error", db_path=db_path, error=str(exc))
        raise
    finally:
        conn.close()

    results = [
        {
            "chunk_text": row[0],
            "source": row[1],
            "article": row[2],
            "page": row[3],
            "score": row[4],
        }
        for row in rows
    ]
    logger.info("retrieve_done", query=query, top_k=top_k, results=len(results))
    return results
