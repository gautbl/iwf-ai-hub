# 04: GLOSSARY.md et ADR

**What to build:** Le glossaire du domaine IWF et les decisions d'architecture sont documentees. Un nouveau developpeur comprend le vocabulaire (athlete, competition, chunk, session) et les choix techniques (Ollama local, DuckDB VSS, pas de cloud).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Creer `GLOSSARY.md` avec les termes du domaine IWF
- [ ] Creer `docs/adr/0001-architecture-souveraine.md` (Ollama local, DuckDB fichier, pas de cloud)
- [ ] Creer `docs/adr/0002-duckdb-vss-pour-rag.md` (DuckDB VSS, index HNSW, trade-off persistence)