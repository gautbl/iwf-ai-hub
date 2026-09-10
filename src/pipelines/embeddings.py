import duckdb
import requests
import structlog
from typing import Dict, List

logger = structlog.get_logger()

# Dimension du modèle d'embedding Ollama nomic-embed-text.
EMBEDDING_DIM = 768


class EmbeddingGenerator:
    """Génère des embeddings via Ollama local et les stocke dans DuckDB VSS."""

    def __init__(self, ollama_url: str, db_path: str,
                 model_name: str = "nomic-embed-text", timeout: int = 30):
        self.ollama_url = ollama_url.rstrip("/")
        self.db_path = db_path
        self.model_name = model_name
        self.timeout = timeout

    def embed_text(self, text: str) -> List[float]:
        """Vectorise un texte via l'API Ollama locale.

        Args:
            text: texte à vectoriser.

        Returns:
            Le vecteur d'embedding (dimension 768).

        Raises:
            requests.exceptions.ConnectionError: Ollama injoignable.
            requests.exceptions.Timeout: délai dépassé.
            RuntimeError: réponse HTTP différente de 200.
            ValueError: dimension du vecteur différente de 768.
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
            logger.error(
                "ollama_http_error", url=url, status_code=response.status_code
            )
            raise RuntimeError(f"Ollama returned HTTP {response.status_code}")

        vector = response.json()["embedding"]
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(f"Dimension inattendue : {len(vector)}")
        return vector

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Vectorise une liste de textes.

        L'endpoint Ollama /api/embeddings accepte un seul prompt par requête,
        d'où des appels unitaires plutôt qu'un batch.

        Args:
            texts: textes à vectoriser.

        Returns:
            Liste de vecteurs d'embedding.
        """
        return [self.embed_text(text) for text in texts]

    def store_chunks(self, chunks: List[Dict], table_name: str = "chunks") -> int:
        """Stocke les chunks vectorisés dans DuckDB (idempotent par id).

        La table est créée par init.sql (source de vérité du schéma) ; ce
        module ne la recrée pas.

        Args:
            chunks: liste de dicts {id, source, article, page, chunk_text}.
            table_name: nom de la table cible.

        Returns:
            Le nombre de chunks réellement insérés (les doublons sont ignorés).
        """
        conn = duckdb.connect(self.db_path)
        inserted = 0
        try:
            # L'index HNSW de la table chunks impose de charger vss dans
            # la session courante avant toute modification de la table.
            conn.execute("INSTALL vss;")
            conn.execute("LOAD vss;")
            for chunk in chunks:
                exists = conn.execute(
                    f"SELECT count(*) FROM {table_name} WHERE id = ?::UUID",
                    [chunk["id"]],
                ).fetchone()[0]
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
