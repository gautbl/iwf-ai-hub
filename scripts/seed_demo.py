#!/usr/bin/env python3
"""scripts/seed_demo.py — Load IWF demo data.

Downloads:
  1. The IWF TCRR PDF (Technical and Competition Rules & Regulations).
  2. Result CSVs from openweightlifting (events 117, 119, 120).

Then runs the pipeline: load -> chunk -> embed -> store in DuckDB.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import structlog

# Add project root so src/ imports work.
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(30))
logger = structlog.get_logger()

# URLs
IWF_PDF_URL = "https://iwf.sport/wp-content/uploads/downloads/2026/10/IWF-TCRR-2026.pdf"
OW_BASE_URL = (
    "https://raw.githubusercontent.com/euanwm/openweightlifting/"
    "development/event_data/IWF"
)
EVENT_IDS = [117, 119, 120]

# Local paths
PDF_DIR = PROJECT_DIR / "data" / "pdfs"
CSV_DIR = PROJECT_DIR / "dbt" / "seeds"
DB_PATH = PROJECT_DIR / "data" / "duckdb" / "iwf_hub.duckdb"
INIT_SQL = PROJECT_DIR / "src" / "db" / "init.sql"


def download_file(url: str, dest: Path) -> None:
    """Download a file from url and write it to dest.

    Args:
        url: Source URL.
        dest: Local destination path.

    Raises:
        requests.exceptions.RequestException: Download failed.
    """
    import requests

    logger.info("download_start", url=url, dest=str(dest))
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    dest.write_bytes(response.content)
    logger.info("download_done", url=url, size=len(response.content))


def init_database(db_path: Path, sql_path: Path) -> None:
    """Create tables in the DuckDB database from init.sql.

    Args:
        db_path: Path to the DuckDB file.
        sql_path: Path to the init SQL file.
    """
    import duckdb

    conn = duckdb.connect(str(db_path))
    try:
        sql = sql_path.read_text()
        conn.execute(sql)
    finally:
        conn.close()
    logger.info("db_initialised", db_path=str(db_path))


def load_csvs(db_path: Path, csv_dir: Path) -> None:
    """Load result CSVs into DuckDB table raw_ow_events.

    Each CSV is an event result file. The loader inserts rows
    labelled with the event id.

    Args:
        db_path: Path to the DuckDB file.
        pdf_dir: Directory containing the CSV files.
    """
    import pandas as pd
    from src.pipelines.extract_results import DataLoader

    loader = DataLoader(str(db_path))
    for event_id in EVENT_IDS:
        csv_path = csv_dir / f"{event_id}.csv"
        df = pd.read_csv(str(csv_path))
        loader.load_to_duckdb(df, "ow_events", event_id=event_id)
        logger.info("csv_loaded", event_id=event_id, rows=len(df))


def run_rag_pipeline(db_path: Path, pdf_dir: Path) -> None:
    """Run RAG pipeline: load PDFs -> chunk -> embed -> store.

    Args:
        db_path: Path to the DuckDB file.
        pdf_dir: Directory containing the PDF files.
    """
    from src.pipelines.chunking import JuridicalChunker
    from src.pipelines.embeddings import EmbeddingGenerator
    from src.pipelines.load_pdfs import load_pdfs

    docs = load_pdfs(str(pdf_dir))
    logger.info("pdfs_loaded", page_count=len(docs))

    chunker = JuridicalChunker(chunk_size=512, chunk_overlap=50)
    chunks: list[dict] = []
    for doc in docs:
        src = doc["metadata"]["source"]
        page = doc["metadata"]["page"]
        chunks.extend(chunker.chunk_text(doc["text"], source=src, page=page))
    logger.info("chunks_generated", chunk_count=len(chunks))

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434",
        db_path=str(db_path),
        model_name="nomic-embed-text",
    )
    inserted = generator.store_chunks(chunks)
    logger.info("embeddings_stored", inserted=inserted)


def main() -> None:
    """Run the full seed pipeline."""
    step = 1

    # Step 1: create directories
    print(f"\n[{step}/6] Creating directories...")
    step += 1
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Step 2: download PDF (manual for now — Cloudflare blocks automated requests)
    pdf_dest = PDF_DIR / "iwf_tcrr_2026.pdf"
    if not pdf_dest.exists():
        print(f"[{step}/6] SKIP: Download IWF TCRR PDF manually to {pdf_dest}")
        print(f"       URL: {IWF_PDF_URL}")
    else:
        print(f"[{step}/6] PDF already exists at {pdf_dest}")
    step += 1

    # Step 3: download CSVs
    print(f"[{step}/6] Downloading result CSVs...")
    step += 1
    for event_id in EVENT_IDS:
        csv_dest = CSV_DIR / f"{event_id}.csv"
        download_file(f"{OW_BASE_URL}/{event_id}.csv", csv_dest)

    # Step 4: initialise DB
    print(f"[{step}/6] Initialising DuckDB database...")
    step += 1
    init_database(DB_PATH, INIT_SQL)

    # Step 5: load CSVs
    print(f"[{step}/6] Loading CSVs into DuckDB...")
    step += 1
    load_csvs(DB_PATH, CSV_DIR)

    # Step 6: RAG pipeline
    #if pdf_dest.exists():
    #    print(f"[{step}/6] RAG pipeline: chunks and embeddings...")
    #    run_rag_pipeline(DB_PATH, PDF_DIR)
    #else:
    #    print(f"[{step}/6] SKIP: RAG pipeline needs PDF at {pdf_dest}")
    #    print("       Download the PDF manually, then re-run this script.")

    print("\n=== seed_demo.py finished ===")


if __name__ == "__main__":
    main()
