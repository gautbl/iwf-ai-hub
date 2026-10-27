"""IWF FastAPI API tests (Phase 5).

Conventions pytest-conventions: docstrings in English, variable names in
English, no real network calls or real Ollama. The application is
built via the ``create_app`` factory; the LangGraph agent is
replaced by a double via ``app.dependency_overrides`` and the
network checks (DuckDB / Ollama) are neutralised by ``monkeypatch``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from src.api import main as api_main
from src.api.dependencies import get_agent_app
from src.api.main import create_app
from src.api.models import ComponentHealth

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeAgentApp:
    """Minimal compilable LangGraph: captures invocations and returns an AIMessage."""

    def __init__(self, response: str = "simulated response") -> None:
        self.response = response
        self.invocations: list[tuple[dict, dict | None]] = []

    def invoke(self, payload: dict, config: dict | None = None) -> dict:
        self.invocations.append((payload, config))
        return {
            "messages": [AIMessage(content=self.response)],
            "retrieved_docs": [],
            "tool_calls": [],
            "session_id": payload["session_id"],
        }


class BoomAgent:
    """Compilable LangGraph that raises an exception on every invocation."""

    def invoke(self, payload: dict, config: dict | None = None) -> dict:
        raise RuntimeError("LLM exploded")


@pytest.fixture
def fake_agent() -> FakeAgentApp:
    """Fake agent shared between tests."""
    return FakeAgentApp()


@pytest.fixture
def healthy_checks(monkeypatch) -> None:
    """Neutralises /health network checks (duckdb + ollama OK)."""
    monkeypatch.setattr(
        api_main,
        "_check_duckdb",
        lambda path: ComponentHealth(name="duckdb", status="ok"),
    )
    monkeypatch.setattr(
        api_main,
        "_check_ollama",
        lambda url: ComponentHealth(name="ollama", status="ok"),
    )


@pytest.fixture
def client(fake_agent: FakeAgentApp, healthy_checks: None) -> Iterator[TestClient]:
    """FastAPI client ready to use: dependencies replaced, subsystems OK."""
    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: fake_agent
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_ok(client: TestClient) -> None:
    """GET /health returns 200 and the duckdb + ollama list when all is well."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app_name"] == "IWF AI Hub API"
    assert body["app_version"] == "0.1.0"
    assert {c["name"] for c in body["components"]} == {"duckdb", "ollama"}


def test_health_degraded_when_ollama_unreachable(
    monkeypatch, fake_agent: FakeAgentApp
) -> None:
    """When Ollama is down, /health returns status='degraded' with the culprit."""
    monkeypatch.setattr(
        api_main,
        "_check_duckdb",
        lambda path: ComponentHealth(name="duckdb", status="ok"),
    )
    monkeypatch.setattr(
        api_main,
        "_check_ollama",
        lambda url: ComponentHealth(
            name="ollama", status="degraded", detail="connection refused"
        ),
    )

    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: fake_agent
    with TestClient(app) as c:
        resp = c.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    by_name = {c["name"]: c for c in body["components"]}
    assert by_name["ollama"]["status"] == "degraded"
    assert "connection refused" in by_name["ollama"]["detail"]
    assert by_name["duckdb"]["status"] == "ok"


# ---------------------------------------------------------------------------
# /chat : Pydantic validation
# ---------------------------------------------------------------------------


def test_chat_rejects_empty_query(client: TestClient) -> None:
    """POST /chat with empty query -> 422 (Pydantic min_length=1)."""
    resp = client.post("/chat", json={"query": ""})
    assert resp.status_code == 422


def test_chat_rejects_too_long_query(client: TestClient) -> None:
    """POST /chat with query > 2000 chars -> 422 (Pydantic max_length=2000)."""
    resp = client.post("/chat", json={"query": "x" * 2001})
    assert resp.status_code == 422


def test_chat_accepts_query_at_max_length(client: TestClient) -> None:
    """POST /chat with exactly 2000 chars -> 200 (inclusive limit)."""
    resp = client.post("/chat", json={"query": "x" * 2000})
    assert resp.status_code == 200


def test_chat_rejects_missing_query_key(client: TestClient) -> None:
    """POST /chat without ``query`` key in JSON -> 422 (Pydantic required field)."""
    resp = client.post("/chat", json={"session_id": "sess-x"})
    assert resp.status_code == 422


def test_chat_rejects_whitespace_only_query(client: TestClient) -> None:
    """POST /chat with whitespace-only query -> 422 (field_validator)."""
    resp = client.post("/chat", json={"query": "   \n\t  "})
    assert resp.status_code == 422
    # The API never invokes the agent for an invalid payload.
    assert resp.json()["detail"][0]["msg"].startswith(
        "query cannot be composed only of spaces"
    ) or any("spaces" in err.get("msg", "") for err in resp.json()["detail"])


# ---------------------------------------------------------------------------
# /chat : session_id handling
# ---------------------------------------------------------------------------


def test_chat_generates_uuid_when_session_id_empty(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """If session_id is empty, the API generates a UUID4 (36 chars) and the checkpointer thread_id."""
    resp = client.post("/chat", json={"query": "Hello?"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["session_id"]) == 36

    payload, config = fake_agent.invocations[-1]
    assert config is not None
    assert config["configurable"]["thread_id"] == body["session_id"]


def test_chat_preserves_explicit_session_id(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """If session_id is provided, the API does not modify it (neither input nor checkpointer)."""
    resp = client.post("/chat", json={"query": "ping", "session_id": "sess-42"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-42"

    payload, config = fake_agent.invocations[-1]
    assert payload["session_id"] == "sess-42"
    assert config is not None
    assert config["configurable"]["thread_id"] == "sess-42"


def test_chat_treats_whitespace_only_session_id_as_empty(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """A session_id composed only of spaces is considered empty."""
    resp = client.post("/chat", json={"query": "ping", "session_id": "   "})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["session_id"]) == 36


# ---------------------------------------------------------------------------
# /chat : contract with the agent
# ---------------------------------------------------------------------------


def test_chat_sends_human_message_to_agent(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """The API sends a HumanMessage (content = query) to the agent, no extra message."""
    resp = client.post("/chat", json={"query": "snatch rules?"})
    assert resp.status_code == 200

    payload, _ = fake_agent.invocations[-1]
    assert len(payload["messages"]) == 1
    msg = payload["messages"][0]
    assert isinstance(msg, HumanMessage)
    assert msg.content == "snatch rules?"


def test_chat_returns_agent_text_in_response(client: TestClient) -> None:
    """The HTTP response contains the text content produced by the agent."""
    app = create_app()
    agent = FakeAgentApp(response="Article 5 applies.")
    app.dependency_overrides[get_agent_app] = lambda: agent

    with TestClient(app) as c:
        resp = c.post("/chat", json={"query": "?"})

    assert resp.status_code == 200
    assert resp.json()["response"] == "Article 5 applies."


# ---------------------------------------------------------------------------
# /chat : error handling
# ---------------------------------------------------------------------------


def test_health_degraded_when_duckdb_unreachable(
    monkeypatch, fake_agent: FakeAgentApp
) -> None:
    """When DuckDB is unreachable, /health returns status='degraded' with the culprit."""
    monkeypatch.setattr(
        api_main,
        "_check_duckdb",
        lambda path: ComponentHealth(
            name="duckdb", status="degraded", detail="cannot open database"
        ),
    )
    monkeypatch.setattr(
        api_main,
        "_check_ollama",
        lambda url: ComponentHealth(name="ollama", status="ok"),
    )

    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: fake_agent
    with TestClient(app) as c:
        resp = c.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    by_name = {c["name"]: c for c in body["components"]}
    assert by_name["duckdb"]["status"] == "degraded"
    assert "cannot open database" in by_name["duckdb"]["detail"]
    assert by_name["ollama"]["status"] == "ok"


def test_check_duckdb_ok(monkeypatch) -> None:
    """Checks that _check_duckdb returns ok when DuckDB responds."""
    from src.api import main as api_main

    class FakeConn:
        def execute(self, sql):
            self._fetched = True
            return self

        def fetchall(self):
            return [(1,)]

        def close(self):
            pass

    monkeypatch.setattr(
        api_main.duckdb, "connect", lambda path, read_only=False: FakeConn()
    )

    result = api_main._check_duckdb("valid.duckdb")
    assert result.status == "ok"


def test_check_duckdb_degraded_on_failure(monkeypatch) -> None:
    """Checks that _check_duckdb returns degraded when DuckDB is unreachable."""
    from src.api import main as api_main

    def broken_connect(*args, **kwargs):
        raise RuntimeError("cannot open database file")

    monkeypatch.setattr(api_main.duckdb, "connect", broken_connect)

    result = api_main._check_duckdb("invalid/path.duckdb")
    assert result.status == "degraded"
    assert "cannot open database" in result.detail


def test_check_ollama_ok(monkeypatch) -> None:
    """Checks that _check_ollama returns ok when Ollama responds."""
    from src.api import main as api_main

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

    monkeypatch.setattr(api_main.requests, "get", lambda *a, **kw: FakeResp())

    result = api_main._check_ollama("http://localhost:11434")
    assert result.status == "ok"


def test_check_ollama_degraded_on_connection_error(monkeypatch) -> None:
    """Checks that _check_ollama returns degraded when Ollama is unreachable."""
    import requests

    from src.api import main as api_main

    def broken_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(api_main.requests, "get", broken_get)

    result = api_main._check_ollama("http://localhost:11434")
    assert result.status == "degraded"
    assert "connection refused" in result.detail


def test_check_ollama_degraded_on_timeout(monkeypatch) -> None:
    """Checks that _check_ollama returns degraded on timeout."""
    import requests

    from src.api import main as api_main

    def timeout_get(*args, **kwargs):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(api_main.requests, "get", timeout_get)

    result = api_main._check_ollama("http://localhost:11434")
    assert result.status == "degraded"
    assert "timeout" in result.detail


def test_health_degraded_when_both_unreachable(
    monkeypatch, fake_agent: FakeAgentApp
) -> None:
    """When both DuckDB and Ollama are down, /health returns status='degraded'."""
    monkeypatch.setattr(
        api_main,
        "_check_duckdb",
        lambda path: ComponentHealth(
            name="duckdb", status="degraded", detail="database missing"
        ),
    )
    monkeypatch.setattr(
        api_main,
        "_check_ollama",
        lambda url: ComponentHealth(name="ollama", status="degraded", detail="timeout"),
    )

    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: fake_agent
    with TestClient(app) as c:
        resp = c.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    by_name = {c["name"]: c for c in body["components"]}
    assert by_name["duckdb"]["status"] == "degraded"
    assert by_name["ollama"]["status"] == "degraded"


def test_chat_returns_500_when_agent_explodes(monkeypatch) -> None:
    """An agent exception becomes a 500 without leaking the original message."""
    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: BoomAgent()
    monkeypatch.setattr(
        api_main,
        "_check_duckdb",
        lambda path: ComponentHealth(name="duckdb", status="ok"),
    )
    monkeypatch.setattr(
        api_main,
        "_check_ollama",
        lambda url: ComponentHealth(name="ollama", status="ok"),
    )

    with TestClient(app) as c:
        resp = c.post("/chat", json={"query": "ping"})

    assert resp.status_code == 500
    assert "LLM exploded" not in resp.text
    assert "Internal agent error" in resp.text


class SilentAgent:
    """Compilable LangGraph that returns a state with no messages (aborted loop)."""

    def invoke(self, payload: dict, config: dict | None = None) -> dict:
        return {
            "messages": [],
            "retrieved_docs": [],
            "tool_calls": [],
            "session_id": payload.get("session_id", ""),
        }


def test_chat_returns_502_when_agent_yields_no_messages(monkeypatch) -> None:
    """If the agent returns ``messages: []``, the API responds 502 (not 500 IndexError)."""
    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: SilentAgent()
    monkeypatch.setattr(
        api_main,
        "_check_duckdb",
        lambda path: ComponentHealth(name="duckdb", status="ok"),
    )
    monkeypatch.setattr(
        api_main,
        "_check_ollama",
        lambda url: ComponentHealth(name="ollama", status="ok"),
    )

    with TestClient(app) as c:
        resp = c.post("/chat", json={"query": "ping"})

    assert resp.status_code == 502
    assert "produced no response" in resp.text


def test_get_agent_app_delegates_to_get_app(monkeypatch) -> None:
    """Checks that get_agent_app() calls get_app imported from graph."""
    from src.api import dependencies

    called = False

    def fake_get_app() -> str:
        nonlocal called
        called = True
        return "fake_app"

    monkeypatch.setattr(dependencies, "get_app", fake_get_app)

    result = dependencies.get_agent_app()

    assert called is True
    assert result == "fake_app"


def test_get_agent_app_propagates_exception(monkeypatch) -> None:
    """Checks that get_agent_app() propagates the exception when get_app() fails.

    If the DuckDB database is unreachable, get_app() raises an exception
    that must propagate via get_agent_app() up to the endpoint.
    """
    from src.api import dependencies

    def broken_get_app() -> str:
        raise RuntimeError("DuckDB unavailable")

    monkeypatch.setattr(dependencies, "get_app", broken_get_app)

    with pytest.raises(RuntimeError, match="DuckDB unavailable"):
        dependencies.get_agent_app()


def test_chat_returns_500_when_get_agent_app_fails() -> None:
    """When get_app() fails (e.g. DuckDB missing), POST /chat returns 500.

    The exception rises during Depends(get_agent_app) resolution. We
    replace the dependency via dependency_overrides so it raises.
    """
    from src.api import dependencies

    def broken_get_agent_app():
        raise RuntimeError("DuckDB connection failed")

    app = create_app()
    app.dependency_overrides[dependencies.get_agent_app] = broken_get_agent_app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.post("/chat", json={"query": "ping"})

    assert resp.status_code == 500
    # The exception in the dependency is caught by Starlette,
    # not by the handler (which is never reached)
    assert "Internal Server Error" in resp.text


# ---------------------------------------------------------------------------
# Factory and configuration
# ---------------------------------------------------------------------------


def test_create_app_returns_distinct_instances() -> None:
    """Two calls to create_app() produce two distinct FastAPI instances (no global singleton)."""
    a = create_app()
    b = create_app()
    assert a is not b


def test_create_app_uses_settings_title_and_version() -> None:
    """OpenAPI metadata (title, version) comes from Settings."""
    app = create_app()
    assert app.title == "IWF AI Hub API"
    assert app.version == "0.1.0"


def test_create_app_registers_expected_routes() -> None:
    """Routes GET /health and POST /chat are registered on the application."""
    app = create_app()
    routes = {
        (r.path, tuple(sorted(r.methods)))  # type: ignore[attr-defined]
        for r in app.routes
        if hasattr(r, "methods")
    }
    assert ("/health", ("GET",)) in routes
    assert ("/chat", ("POST",)) in routes