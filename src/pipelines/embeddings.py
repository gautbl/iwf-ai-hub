import duckdb
import requests
import structlog

logger = structlog.get_logger()

# Dimension of the Ollama nomic-embed-text embedding model.
EMBEDDING_DIM = 768


class EmbeddingGenerator:
    """Generates embeddings via local Ollama and stores in DuckDB VSS."""

    def __init__(
        self,
        ollama_url: str,
        db_path: str,
        model_name: str = "nomic-embed-text",
        timeout: int = 30,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.db_path = db_path
        self.model_name = model_name
        self.timeout = timeout

    def embed_text(self, text: str) -> list[float]:
        """Vectorises text via the local Ollama API.

        Args:
            text: text to vectorise.

        Returns:
            The embedding vector (dimension 768).

        Raises:
            requests.exceptions.ConnectionError: Ollama unreachable.
            requests.exceptions.Timeout: timeout exceeded.
            RuntimeError: HTTP response different from 200.
            ValueError: vector dimension different from 768.
        """
        url = f"{self.ollama_url}/api/embeddings"
        payload = {"model": self.model_name, "prompt": text}

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.exceptions.ConnectionError as exc:
            logger.error("ollama_connection_error", url=url, error=str(exc))
            raise
        except requests.exceptions.Timeout as exc:
            logger.error("ollama_timeout", url=url, error=str(exc))
            raise

        if response.status_code != 200:
            logger.error("ollama_http_error", url=url, status_code=response.status_code)
            raise RuntimeError(f"Ollama returned HTTP {response.status_code}")

        vector = response.json()["embedding"]
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(f"Unexpected dimension: {len(vector)}")
        return vector

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Vectorises a list of texts.

        The Ollama /api/embeddings endpoint accepts one prompt per request,
        hence single calls instead of a batch.

        Args:
            texts: texts to vectorise.

        Returns:
            List of embedding vectors.
        """
        return [self.embed_text(text) for text in texts]

    def store_chunks(self, chunks: list[dict], table_name: str = "chunks") -> int:
        """Stores vectorised chunks in DuckDB (idempotent by id).

        The table is created by init.sql (schema source of truth). This
        module does not recreate it.

        Args:
            chunks: list of dicts {id, source, article, page, chunk_text}.
            table_name: name of the target table.

        Returns:
            The number of chunks actually inserted (duplicates are skipped).
        """
        conn = duckdb.connect(self.db_path)
        inserted = 0
        try:
            # The HNSW index on the chunks table requires loading vss in
            # the current session before any table modification.
            conn.execute("INSTALL vss;")
            conn.execute("LOAD vss;")
            for chunk in chunks:
                result = conn.execute(
                    f"SELECT count(*) FROM {table_name} WHERE id = ?::UUID",
                    [chunk["id"]],
                ).fetchone()
                exists = result[0] if result else 0
                if exists:
                    logger.info("chunk_skipped", chunk_id=chunk["id"])
                    continue

                vector = self.embed_text(chunk["chunk_text"])
                conn.execute(
                    f"""
                    INSERT INTO {table_name}
                    (id, source, article, page, chunk_text, embedding)
                    VALUES (?::UUID, ?, ?, ?, ?, ?::FLOAT[{EMBEDDING_DIM}])
                    """,
                    [
                        chunk["id"],
                        chunk["source"],
                        chunk.get("article"),
                        chunk.get("page"),
                        chunk["chunk_text"],
                        vector,
                    ],
                )
                inserted += 1
        finally:
            conn.close()

        logger.info("chunks_stored", table_name=table_name, inserted=inserted)
        return inserted