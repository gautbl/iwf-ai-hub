# 02: Seed and startup

**What to build:** Public IWF data (TCRR PDF + openweightlifting CSV) loads automatically. Embeddings and the VSS index generate on startup. Ollama models are available.

**Blocked by:** 01 (Dockerise the API)

**Status:** partial

- [x] `scripts/seed_demo.sh` : a `curl` on each URL returns 200 AND the DB contains non-empty `raw_ow_events` and `chunks` after execution
- [x] `scripts/startup.sh` : DB absent → exit 1. DB present and index absent → VSS query succeeds after rebuild
- [x] `data/duckdb/test_iwf_hub.duckdb` added to `.gitignore`
- [ ] Manual verification: `docker-compose up` + seed → `curl localhost:8000/chat` returns a contextual response (blocked: needs a Docker environment with Ollama)