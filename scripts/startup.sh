#!/usr/bin/env bash
set -euo pipefail

# scripts/startup.sh - Startup verification and initialisation
#
# Runs when the API container starts (or manually).
# 1. Checks the DuckDB database exists and is readable
# 2. Checks / pulls required Ollama models (llama3.2, nomic-embed-text)
# 3. Rebuilds the HNSW VSS index on the chunks table (not persistent across sessions)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration (overridable by environment variables)
DUCKDB_PATH="${IWF_DUCKDB_PATH:-${PROJECT_DIR}/data/duckdb/iwf_hub.duckdb}"
OLLAMA_URL="${IWF_OLLAMA_URL:-http://localhost:11434}"
EMBEDDING_MODEL="nomic-embed-text"
LLM_MODEL="llama3.2"

echo "=== startup.sh — IWF Hub Startup ==="
echo ""

# ------- 1. Check DuckDB database ----------------------------------------
echo "[1/3] Checking DuckDB database..."
if [ ! -f "$DUCKDB_PATH" ]; then
    echo "  !! Database not found: ${DUCKDB_PATH}"
    echo "  >> Run scripts/seed_demo.sh first to create the database."
    exit 1
fi

python3 << PYEOF
import duckdb
conn = duckdb.connect('${DUCKDB_PATH}', read_only=True)
try:
    conn.execute('SELECT 1').fetchall()
    print('  OK Database readable')
finally:
    conn.close()
PYEOF

# ------- 2. Pull Ollama models --------------------------------------------
echo "[2/3] Checking Ollama models..."

check_and_pull() {
    local model="$1"
    if curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "import sys,json; models=json.load(sys.stdin).get('models',[]); sys.exit(0 if any(m['name'].startswith('${model}') for m in models) else 1)" 2>/dev/null; then
        echo "  OK Model ${model} already present"
    else
        echo "  >> Pulling model ${model}..."
        curl -sf -X POST "${OLLAMA_URL}/api/pull" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"${model}\"}" > /dev/null
        echo "  OK Model ${model} downloaded"
    fi
}

check_and_pull "$EMBEDDING_MODEL"
check_and_pull "$LLM_MODEL"

# ------- 3. Rebuild HNSW VSS index -----------------------------------
echo "[3/3] Rebuilding HNSW VSS index..."
python3 << PYEOF
import duckdb

conn = duckdb.connect('${DUCKDB_PATH}')
conn.execute('INSTALL vss')
conn.execute('LOAD vss')
# Check if the chunks table exists and has data
tables = conn.execute(
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='chunks'"
).fetchone()[0]

if tables == 0:
    print("  !! Table chunks absent - run seed_demo.sh first")
else:
    count = conn.execute('SELECT count(*) FROM chunks').fetchone()[0]
    if count == 0:
        print("  !! Table chunks empty - run seed_demo.sh first")
    else:
        # Recreate the HNSW index (does not persist across DuckDB sessions)
        conn.execute('DROP INDEX IF EXISTS idx_chunks')
        conn.execute("""
            CREATE INDEX idx_chunks ON chunks
            USING HNSW (embedding)
            WITH (metric = 'cosine', ef_construction = 200, M = 16)
        """)
        print(f'  OK HNSW index rebuilt on {count} chunks')
conn.close()
PYEOF

echo ""
echo "=== startup.sh finished - Ready for /chat ==="