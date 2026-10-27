from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import json
import os
import sys
import duckdb
import requests
import structlog

sys.path.insert(0, '/opt/airflow')

from src.pipelines.load_pdfs import load_pdfs
from src.pipelines.chunking import JuridicalChunker
from src.pipelines.embeddings import EmbeddingGenerator

logger = structlog.get_logger()

# Configuration
PDF_URLS = [
    "https://www.iwf.net/wp-content/uploads/downloads/2024/01/IWF_TCRR_2024.pdf",
]
DB_PATH = "/data/duckdb/iwf_hub.duckdb"
PDF_DIR = "/data/pdfs"
OLLAMA_URL = "http://ollama:11434"  # Local Ollama, Docker network
EMBEDDING_MODEL = "nomic-embed-text"
INIT_SQL_PATH = "/opt/airflow/src/db/init.sql"

def init_database():
    """Initialises the DuckDB database (VSS extension, chunks table, HNSW index)."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if not os.path.exists(INIT_SQL_PATH):
        raise FileNotFoundError(f"init.sql not found: {INIT_SQL_PATH}")

    with open(INIT_SQL_PATH, encoding="utf-8") as f:
        init_sql = f.read()

    conn = duckdb.connect(DB_PATH)
    try:
        conn.execute(init_sql)
    finally:
        conn.close()

    logger.info("db_initialized", db_path=DB_PATH)

def download_pdfs():
    """Downloads IWF regulation PDFs from the official site.""""
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

    return f"Downloaded: {len(downloaded)} PDFs"

def process_and_chunk():
    """Extracts text from PDFs and splits into regulation chunks.""""
    chunker = JuridicalChunker(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    # Process all PDFs
    all_chunks = []
    documents = load_pdfs(PDF_DIR)
    for doc in documents:
        source = doc["metadata"]["source"]
        page = doc["metadata"]["page"]
        try:
            # page propagates from load_pdfs; article is detected
            # then stored in each chunk by the chunker.
            chunks = chunker.chunk_text(doc["text"], source=source, page=page)
            all_chunks.extend(chunks)
            logger.info("chunked", source=source, page=page, count=len(chunks))
        except Exception as e:
            logger.warning("chunk_failed", source=source, page=page, error=str(e))

    # Save chunks temporarily for the next task
    chunks_file = os.path.join(PDF_DIR, "chunks_temp.json")
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    return f"Chunks created: {len(all_chunks)}"

def generate_embeddings():
    """Generates embeddings via local Ollama and stores in DuckDB VSS."""
    chunks_file = os.path.join(PDF_DIR, "chunks_temp.json")
    if not os.path.exists(chunks_file):
        raise FileNotFoundError("Chunks file not found. Run process_and_chunk first.")

    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    embedder = EmbeddingGenerator(
        ollama_url=OLLAMA_URL,
        db_path=DB_PATH,
        model_name=EMBEDDING_MODEL,
    )

    # article and page are already carried by each chunk
    inserted = embedder.store_chunks(chunks, table_name="chunks")

    # Cleanup
    os.remove(chunks_file)

    return f"{inserted} chunks vectorised and stored"

with DAG(
    dag_id='iwf_rag_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@monthly',  # Less frequent than the ETL
    catchup=False,
    tags=['iwf', 'rag', 'regulation']
) as dag:

    init_db_task = PythonOperator(
        task_id='init_db',
        python_callable=init_database
    )

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

    init_db_task >> download_task >> chunk_task >> embed_task
