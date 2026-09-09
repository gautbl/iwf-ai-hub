import duckdb
import numpy as np
from sentence_transformers import SentenceTransformer
import structlog
from typing import List, Dict

logger = structlog.get_logger()

class EmbeddingGenerator:
    def __init__(self, model_name: str, ollama_url: str, db_path: str):
        self.model = SentenceTransformer(model_name)
        self.db_path = db_path
        self.ollama_url = ollama_url
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Génère les embeddings pour une liste de textes"""
        return self.model.encode(texts, show_progress_bar=True)
    
    def store_chunks(self, chunks: List[Dict], table_name: str = "documents"):
        """Stocke les chunks avec leurs embeddings dans DuckDB VSS"""
        conn = duckdb.connect(self.db_path)
        
        # Créer l'extension VSS si pas déjà fait
        conn.execute("INSTALL vss;")
        conn.execute("LOAD vss;")
        
        # Créer la table si elle n'existe pas
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id VARCHAR PRIMARY KEY,
                text TEXT,
                source VARCHAR,
                position INTEGER,
                char_start INTEGER,
                char_end INTEGER,
                embedding FLOAT[384]  -- Dimension pour MiniLM-L12
            )
        """)
        
        # Générer les embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.generate_embeddings(texts)
        
        # Insérer les données
        for chunk, emb in zip(chunks, embeddings):
            conn.execute(f"""
                INSERT OR REPLACE INTO {table_name} 
                (id, text, source, position, char_start, char_end, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk["id"], chunk["text"], chunk["source"],
                chunk["position"], chunk["char_start"], chunk["char_end"],
                emb.tolist()
            ))
        
        # Créer l'index HNSW pour la recherche vectorielle
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding 
            ON {table_name} USING HNSW(embedding)
        """)
        
        conn.close()
        logger.info("chunks_stored", table_name=table_name, count=len(chunks))
    
    def search_similar(self, query: str, table_name: str = "documents", 
                       top_k: int = 5) -> List[Dict]:
        """Recherche les chunks similaires à une requête"""
        query_emb = self.model.encode([query])[0]
        
        conn = duckdb.connect(self.db_path)
        conn.execute("LOAD vss;")
        
        results = conn.execute(f"""
            SELECT id, text, source, position, 
                   array_cosine_similarity(embedding, ?::FLOAT[384]) as similarity
            FROM {table_name}
            ORDER BY similarity DESC
            LIMIT {top_k}
        """, (query_emb.tolist(),)).fetchall()
        
        conn.close()
        return results