#!/usr/bin/env bash
set -euo pipefail

# scripts/seed_demo.sh — Charge les données IWF de démonstration
#
# Télécharge :
#   1. Le PDF IWF TCRR (Technical and Competition Rules & Regulations)
#   2. Les CSV de résultats depuis openweightlifting (events 117, 119, 120)
# Puis exécute le pipeline : load -> chunk -> embed -> store dans DuckDB.

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

# ── 1. Créer les répertoires ──────────────────────────────────────────
mkdir -p "$PDF_DIR"

# ── 2. Télécharger le PDF TCRR ────────────────────────────────────────
echo "[1/4] Téléchargement du PDF IWF TCRR..."
curl -fSL -o "${PDF_DIR}/iwf_tcrr_2026.pdf" "$IWF_PDF_URL"
echo "  ✓ PDF sauvegardé dans ${PDF_DIR}/iwf_tcrr_2026.pdf"

# ── 3. Télécharger les CSV de résultats ───────────────────────────────
echo "[2/4] Téléchargement des CSV de résultats..."
for event_id in "${EVENT_IDS[@]}"; do
    echo "  → Event ${event_id}..."
    curl -fSL -o "${PDF_DIR}/${event_id}.csv" "${OW_BASE_URL}/${event_id}.csv"
    echo "    ✓ ${event_id}.csv"
done

# ── 4. Initialiser la base DuckDB ─────────────────────────────────────
echo "[3/4] Initialisation de la base DuckDB..."
python3 -c "
import duckdb
conn = duckdb.connect('${DUCKDB_PATH}')
with open('${INIT_SQL}') as f:
    conn.execute(f.read())
conn.close()
print('  ✓ Base initialisée')
"

# ── 5. Pipeline RAG : load -> chunk -> embed -> store ─────────────────
echo "[4/4] Pipeline RAG : extraction des chunks et embeddings..."
cd "$PROJECT_DIR"

python3 -c "
import sys
sys.path.insert(0, '.')
import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(30))

from src.pipelines.load_pdfs import load_pdfs
from src.pipelines.chunking import JuridicalChunker
from src.pipelines.embeddings import EmbeddingGenerator

# Contexte : charge les PDFs
docs = load_pdfs('${PDF_DIR}')
print(f'  → {len(docs)} pages extraites des PDFs')

# Chunking
chunker = JuridicalChunker(chunk_size=512, chunk_overlap=50)
chunks = []
for doc in docs:
    src = doc['metadata']['source']
    page = doc['metadata']['page']
    chunks.extend(chunker.chunk_text(doc['text'], source=src, page=page))
print(f'  → {len(chunks)} chunks générés')

# Embedding + stockage
generator = EmbeddingGenerator(
    ollama_url='http://localhost:11434',
    db_path='${DUCKDB_PATH}',
    model_name='nomic-embed-text',
)
inserted = generator.store_chunks(chunks)
print(f'  ✓ {inserted} chunks vectorisés et stockés')
"

echo ""
echo "=== seed_demo.sh terminé ==="