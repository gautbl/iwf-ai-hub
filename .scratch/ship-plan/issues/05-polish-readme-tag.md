# 05: Polish README et tag v1.0.0-alpha.1

**What to build:** README a jour, tag git pose, livrable pret a montrer au client. Un nouveau developpeur ou client suit les instructions et lance le produit.

**Blocked by:** 01 (Dockeriser l'API), 02 (Scripts seed startup), 03 (Page HTML chat)

**Status:** ready-for-agent

- [ ] Mettre a jour README.md avec instructions one-click `docker-compose up`
- [ ] Ajouter section "Demo client" avec URL, exemples de questions
- [ ] Ajouter tableau des endpoints (GET /health, POST /chat, GET /)
- [ ] Creer CHANGELOG.md ou release notes
- [ ] Appliquer le tag `v1.0.0-alpha.1` apres validation des tests
- [ ] Verifier : `pytest tests/` = 81+ tests verts