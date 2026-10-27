# 02: Scripts de seed et startup

**What to build:** Les donnees IWF publiques (PDF reglementation + CSV resultats) sont chargees automatiquement. Les embeddings sont generes. L'index VSS est reconstruit au demarrage. Les modeles Ollama sont disponibles.

**Blocked by:** 01 (Dockeriser l'API)

**Status:** ready-for-agent

- [ ] Creer `scripts/seed_demo.sh` (telecharge PDF, CSV, lance chunking + embeddings)
- [ ] Creer `scripts/startup.sh` (verifie base, pull modeles Ollama si absents, rebuild index HNSW VSS)
- [ ] Ajouter `test_iwf_hub.duckdb` dans `.gitignore`
- [ ] Verifier : apres `docker-compose up`, le chat repond sur les reglementations IWF