#!/usr/bin/env bash
set -euo pipefail

# scripts/startup.sh — Vérification et initialisation au démarrage
#
# Exécuté au lancement du conteneur API (ou manuellement).
# 1. Vérifie que la base DuckDB existe et est lisible
# 2. Vérifie / pull les modèles Ollama nécessaires (llama3.2, nomic-embed-text)
# 3. Reconstruit l'index HNSW VSS sur la table chunks (non persistant entre sessions)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration (surchargeable par variables d'environnement)
DUCKDB_PATH="${IWF_DUCKDB_PATH:-${PROJECT_DIR}/data/duckdb/iwf_hub.duckdb}"
OLLAMA_URL="${IWF_OLLAMA_URL:-http://localhost:11434}"
EMBEDDING_MODEL="nomic-embed-text"
LLM_MODEL="llama3.2"

echo "=== startup.sh — IWF Hub Startup ==="
echo ""

# ── 1. Vérifier la base DuckDB ────────────────────────────────────────
echo "[1/3] Vérification de la base DuckDB..."
if [ ! -f "$DUCKDB_PATH" ]; then
    echo "  ⚠ Base non trouvée : ${DUCKDB_PATH}"
    echo "  → Exécutez d'abord scripts/seed_demo.sh pour créer la base."
    exit 1
fi

python3 << PYEOF
import duckdb
conn = duckdb.connect('${DUCKDB_PATH}', read_only=True)
try:
    conn.execute('SELECT 1').fetchall()
    print('  ✓ Base accessible en lecture')
finally:
    conn.close()
PYEOF

# ── 2. Pull des modèles Ollama ────────────────────────────────────────
echo "[2/3] Vérification des modèles Ollama..."

check_and_pull() {
    local model="$1"
    if curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "import sys,json; models=json.load(sys.stdin).get('models',[]); sys.exit(0 if any(m['name'].startswith('${model}') for m in models) else 1)" 2>/dev/null; then
        echo "  ✓ Modèle ${model} déjà présent"
    else
        echo "  → Pull du modèle ${model}..."
        curl -sf -X POST "${OLLAMA_URL}/api/pull" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"${model}\"}" > /dev/null
        echo "  ✓ Modèle ${model} téléchargé"
    fi
}

check_and_pull "$EMBEDDING_MODEL"
check_and_pull "$LLM_MODEL"

# ── 3. Reconstruire l'index HNSW VSS ─────────────────────────────────
echo "[3/3] Reconstruction de l'index HNSW VSS..."
python3 << PYEOF
import duckdb

conn = duckdb.connect('${DUCKDB_PATH}')
conn.execute('INSTALL vss')
conn.execute('LOAD vss')
# Vérifier si la table chunks existe et contient des données
tables = conn.execute(
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='chunks'"
).fetchone()[0]

if tables == 0:
    print("  ⚠ Table chunks absente — exécutez seed_demo.sh d'abord")
else:
    count = conn.execute('SELECT count(*) FROM chunks').fetchone()[0]
    if count == 0:
        print("  ⚠ Table chunks vide — exécutez seed_demo.sh d'abord")
    else:
        # Recréer l'index HNSW (l'index ne persiste pas entre sessions DuckDB)
        conn.execute('DROP INDEX IF EXISTS idx_chunks')
        conn.execute("""
            CREATE INDEX idx_chunks ON chunks
            USING HNSW (embedding)
            WITH (metric = 'cosine', ef_construction = 200, M = 16)
        """)
        print(f'  ✓ Index HNSW reconstruit sur {count} chunks')
conn.close()
PYEOF

echo ""
echo "=== startup.sh terminé — Prêt pour /chat ==="