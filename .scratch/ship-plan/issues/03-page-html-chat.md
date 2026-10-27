# 03: HTML chat page

**What to build:** A user opens `http://localhost:8000`, sees a text field, asks a question about IWF rules or results, gets a response. The session persists across messages.

**Blocked by:** 01 (Dockerise the API)

**Status:** ready-for-agent

- [ ] Create `src/api/static/index.html` (text field, send button, response area, session_id)
- [ ] Add route `GET /` in `src/api/main.py` that serves the HTML page
- [ ] Calls `POST /chat` via `fetch()` in JavaScript
- [ ] Clean and responsive design
- [ ] Test: `GET /` returns 200 with `text/html`
- [ ] Test: the HTML page contains form elements