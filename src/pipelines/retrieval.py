import os

import duckdb
import requests
import structlog

from src.pipelines.embeddings import EMBEDDING_DIM, EmbeddingGenerator

logger = structlog.get_logger()

# Local Ollama URL (overridable via environment variable in container).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"


def retrieve(query: str, db_path: str, top_k: int = 5) -> list[dict]:
    """Searches for the chunks closest to the query in DuckDB VSS.

    Args:
        query: natural language question.
        db_path: path to the DuckDB database containing the chunks table.
        top_k: maximum number of results to return.

    Returns:
        List of dicts {chunk_text, source, article, page, score} sorted by
        descending score. Empty list if Ollama is unavailable, if the
        returned vector is invalid (RuntimeError / ValueError) or if the
        chunks table is empty.

    Raises:
        duckdb.Error: DuckDB database unreachable or invalid query.
    """
    logger.info("retrieve_start", query=query, top_k=top_k)

    generator = EmbeddingGenerator(
        ollama_url=OLLAMA_URL, db_path=db_path, model_name=EMBEDDING_MODEL
    )

    try:
        query_vector = generator.embed_text(query)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.error("retrieve_ollama_unavailable", error=str(exc))
        return []
    except RuntimeError as exc:
        logger.error("retrieve_runtime_error", error=str(exc))
        return []
    except ValueError as exc:
        logger.error("retrieve_value_error", error=str(exc))
        return []

    conn = None
    try:
        conn = duckdb.connect(db_path)

        # The HNSW index does not persist across DuckDB sessions. Reload
        # the extension and recreate the index if absent.
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
    except RuntimeError as exc:
        logger.error("retrieve_runtime_error", db_path=db_path, error=str(exc))
        return []
    except ValueError as exc:
        logger.error("retrieve_value_error", db_path=db_path, error=str(exc))
        return []
    except duckdb.Error as exc:
        logger.error("retrieve_duckdb_error", db_path=db_path, error=str(exc))
        raise
    finally:
        if conn is not None:
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