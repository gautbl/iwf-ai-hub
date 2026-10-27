#!/usr/bin/env bash
set -euo pipefail

# scripts/seed_demo.sh — Loads IWF demo data
#
# Downloads:
#   1. The IWF TCRR PDF (Technical and Competition Rules & Regulations)
#   2. Result CSVs from openweightlifting (events 117, 119, 120)
# Then runs the pipeline: load -> chunk -> embed -> store in DuckDB.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# URLs
IWF_PDF_URL="https://iwf.sport/wp-content/uploads/downloads/2026/10/IWF-TCRR-2026.pdf"
OW_BASE_URL="https://raw.githubusercontent.com/euanwm/openweightlifting/development/event_data/IWF"
EVENT_IDS=(117 119 120)

# Chemins locaux
PDF_DIR="${PROJECT_DIR}/data/pdfs"
DUCKDB_PATH="${PROJECT_DIR}/data/duckdb/iwf_hub.duckdb"
INIT_SQL="${PROJECT_DIR}/src/db/init.sql"

echo "=== seed_demo.sh — IWF Data Seed ==="
echo ""

# ── 1. Create directories ──────────────────────────────────────────
mkdir -p "$PDF_DIR"

# ── 2. Download the TCRR PDF ────────────────────────────────────────
echo "[1/6] Downloading IWF TCRR PDF..."
curl -fSL -o "${PDF_DIR}/iwf_tcrr_2026.pdf" "$IWF_PDF_URL"
echo "  ✓ PDF saved to ${PDF_DIR}/iwf_tcrr_2026.pdf"

# ── 3. Download result CSVs ───────────────────────────────
echo "[2/6] Downloading result CSVs..."
for event_id in "${EVENT_IDS[@]}"; do
    echo "  → Event ${event_id}..."
    curl -fSL -o "${PDF_DIR}/${event_id}.csv" "${OW_BASE_URL}/${event_id}.csv"
    echo "    ✓ ${event_id}.csv"
done

# ── 4. Initialise the DuckDB database ─────────────────────────────────────
echo "[3/6] Initialising DuckDB database..."
python3 -c "
import duckdb
conn = duckdb.connect('${DUCKDB_PATH}')
with open('${INIT_SQL}') as f:
    conn.execute(f.read())
conn.close()
print('  ✓ Database initialised')
"

# ── 5. Load CSVs into DuckDB (Star Schema raw_ow_events) ────────
echo "[4/6] Loading CSVs into DuckDB..."
python3 -c "
import sys
sys.path.insert(0, '.')
import pandas as pd
from src.pipelines.extract_results import DataLoader

loader = DataLoader('${DUCKDB_PATH}')
for event_id in [117, 119, 120]:
    df = pd.read_csv('${PDF_DIR}/\${event_id}.csv')
    loader.load_to_duckdb(df, 'ow_events', event_id=event_id)
    print(f'  → Event {event_id}: {len(df)} rows loaded')
print('  ✓ CSVs loaded into raw_ow_events')
"

# ── 6. RAG pipeline: load -> chunk -> embed -> store ─────────────────
echo "[6/6] RAG pipeline: chunks and embeddings..."
cd "$PROJECT_DIR"

python3 -c "
import sys
sys.path.insert(0, '.')
import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(30))

from src.pipelines.load_pdfs import load_pdfs
from src.pipelines.chunking import JuridicalChunker
from src.pipelines.embeddings import EmbeddingGenerator

# Context: loads the PDFs
docs = load_pdfs('${PDF_DIR}')
print(f'  → {len(docs)} pages extracted from PDFs')

# Chunking
chunker = JuridicalChunker(chunk_size=512, chunk_overlap=50)
chunks = []
for doc in docs:
    src = doc['metadata']['source']
    page = doc['metadata']['page']
    chunks.extend(chunker.chunk_text(doc['text'], source=src, page=page))
print(f'  → {len(chunks)} chunks generated')

# Embedding + storage
generator = EmbeddingGenerator(
    ollama_url='http://localhost:11434',
    db_path='${DUCKDB_PATH}',
    model_name='nomic-embed-text',
)
inserted = generator.store_chunks(chunks)
print(f'  ✓ {inserted} chunks vectorised and stored')
"

echo ""
echo "=== seed_demo.sh finished ==="