# 05: Polish README and tag v1.0.0-alpha.1

**What to build:** README up to date, git tag set, deliverable ready to show the client. A new developer or client follows the instructions and runs the product.

**Blocked by:** 01 (Dockerise the API), 02 (Seed and startup scripts), 03 (HTML chat page)

**Status:** ready-for-agent

- [ ] Update README.md with one-click `docker-compose up` instructions
- [ ] Add "Client demo" section with URL, question examples
- [ ] Add endpoint table (GET /health, POST /chat, GET /)
- [ ] Create CHANGELOG.md or release notes
- [ ] Apply tag `v1.0.0-alpha.1` after test validation
- [ ] Verify: `pytest tests/` = 81+ tests green