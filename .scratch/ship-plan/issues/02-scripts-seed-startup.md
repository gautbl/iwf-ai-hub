# 02: Seed et startup

**What to build:** Les donnees IWF publiques (PDF TCRR + CSV openweightlifting) sont chargees automatiquement. Les embeddings et l'index VSS sont generes au demarrage. Les modeles Ollama sont disponibles.

**Blocked by:** 01 (Dockeriser l'API)

**Status:** closed

- [x] `scripts/seed_demo.sh` : un `curl` sur chaque URL retourne 200 ET la base contient `raw_ow_events` et `chunks` non vides apres execution
- [x] `scripts/startup.sh` : base absente → exit 1. Base presente et index absent → requete VSS reussie apres rebuild
- [x] `data/duckdb/test_iwf_hub.duckdb` ajoute dans `.gitignore`
- [x] Verification manuelle : `docker-compose up` + seed → `curl localhost:8000/chat` renvoie une reponse contextuelle