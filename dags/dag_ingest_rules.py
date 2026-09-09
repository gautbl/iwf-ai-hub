from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import json
import os
import sys
import requests
import structlog

sys.path.insert(0, '/opt/airflow')

from src.pipelines.load_pdfs import load_pdfs
from src.pipelines.chunking import JuridicalChunker
from src.pipelines.embeddings import EmbeddingGenerator

logger = structlog.get_logger()

# Configuration
PDF_URLS = [
    "https://www.iwf.net/wp-content/uploads/2024/01/IWF-Technical-and-Competition-Rules-2024.pdf",
    "https://www.iwf.net/wp-content/uploads/2024/01/IWF-Anti-Doping-Policy-2024.pdf",
    # Ajoutez d'autres URLs IWF ici
]
DB_PATH = "/data/duckdb/iwf_hub.duckdb"
PDF_DIR = "/data/pdfs"
OLLAMA_URL = "http://ollama:11434"

def download_pdfs():
    """Télécharge les PDFs réglementaires IWF"""
    os.makedirs(PDF_DIR, exist_ok=True)
    downloaded = []

    for url in PDF_URLS:
        try:
            filename = url.split("/")[-1]
            filepath = os.path.join(PDF_DIR, filename)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            downloaded.append(filepath)
            logger.info("pdf_downloaded", filepath=filepath)
        except Exception as e:
            logger.warning("pdf_download_failed", url=url, error=str(e))

    return f"Téléchargés: {len(downloaded)} PDFs"

def process_and_chunk():
    """Extrait le texte et chunk les PDFs"""
    chunker = JuridicalChunker(
        chunk_size=512,  # Tokens
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    # Traiter tous les PDFs
    all_chunks = []
    documents = load_pdfs(PDF_DIR)
    for doc in documents:
        source = doc["metadata"]["source"]
        try:
            chunks = chunker.chunk_text(doc["text"], source=source)
            all_chunks.extend(chunks)
            logger.info("chunked", source=source, count=len(chunks))
        except Exception as e:
            logger.warning("chunk_failed", source=source, error=str(e))

    # Sauvegarder les chunks temporairement pour la tâche suivante
    chunks_file = os.path.join(PDF_DIR, "chunks_temp.json")
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    return f"Chunks créés: {len(all_chunks)}"

def generate_embeddings():
    """Génère les embeddings et stocke en VSS"""
    chunks_file = os.path.join(PDF_DIR, "chunks_temp.json")
    if not os.path.exists(chunks_file):
        raise FileNotFoundError("Fichier chunks non trouvé. Exécutez process_and_chunk d'abord.")

    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    embedder = EmbeddingGenerator(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        ollama_url=OLLAMA_URL,
        db_path=DB_PATH
    )

    # Générer et stocker les embeddings
    embedder.store_chunks(chunks, table_name="documents")

    # Nettoyage
    os.remove(chunks_file)

    return f"✅ {len(chunks)} chunks vectorisés et stockés"

with DAG(
    dag_id='iwf_rag_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@monthly',  # Moins fréquent que l'ETL
    catchup=False,
    tags=['iwf', 'rag', 'reglementation']
) as dag:

    download_task = PythonOperator(
        task_id='download_pdfs',
        python_callable=download_pdfs
    )

    chunk_task = PythonOperator(
        task_id='process_and_chunk',
        python_callable=process_and_chunk
    )

    embed_task = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_embeddings
    )

    download_task >> chunk_task >> embed_task
