"""Tests de l'API FastAPI IWF (Phase 5).

Conventions pytest-conventions : docstrings en français, variables en
anglais, aucun appel réseau ni Ollama réel. L'application est
construite via la factory ``create_app`` ; l'agent LangGraph est
remplacé par un double via ``app.dependency_overrides`` et les
checks réseau (DuckDB / Ollama) sont neutralisés par ``monkeypatch``.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from src.api import main as api_main
from src.api.dependencies import get_agent_app
from src.api.main import create_app
from src.api.models import ComponentHealth


# ---------------------------------------------------------------------------
# Doubles de test
# ---------------------------------------------------------------------------


class FakeAgentApp:
    """Compilable LangGraph minimal : capture les invocations et renvoie un AIMessage."""

    def __init__(self, response: str = "réponse simulée") -> None:
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
    """Compilable LangGraph qui lève une exception à chaque invocation."""

    def invoke(self, payload: dict, config: dict | None = None) -> dict:
        raise RuntimeError("LLM exploded")


@pytest.fixture
def fake_agent() -> FakeAgentApp:
    """Agent factice partagé entre tests."""
    return FakeAgentApp()


@pytest.fixture
def healthy_checks(monkeypatch) -> None:
    """Neutralise les vérifications réseau de /health (duckdb + ollama OK)."""
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
def client(
    fake_agent: FakeAgentApp, healthy_checks: None
) -> Iterator[TestClient]:
    """Client FastAPI prêt à l'emploi : dépendances substituées, sous-systèmes OK."""
    app = create_app()
    app.dependency_overrides[get_agent_app] = lambda: fake_agent
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_ok(client: TestClient) -> None:
    """GET /health renvoie 200 et la liste duckdb + ollama quand tout va bien."""
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
    """Si Ollama est down, /health renvoie status='degraded' et le fautif en clair."""
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
# /chat : validation Pydantic
# ---------------------------------------------------------------------------


def test_chat_rejects_empty_query(client: TestClient) -> None:
    """POST /chat avec query vide -> 422 (Pydantic min_length=1)."""
    resp = client.post("/chat", json={"query": ""})
    assert resp.status_code == 422


def test_chat_rejects_too_long_query(client: TestClient) -> None:
    """POST /chat avec query > 2000 caractères -> 422 (Pydantic max_length=2000)."""
    resp = client.post("/chat", json={"query": "x" * 2001})
    assert resp.status_code == 422


def test_chat_accepts_query_at_max_length(client: TestClient) -> None:
    """POST /chat avec exactement 2000 caractères -> 200 (limite inclusive)."""
    resp = client.post("/chat", json={"query": "x" * 2000})
    assert resp.status_code == 200


def test_chat_rejects_missing_query_key(client: TestClient) -> None:
    """POST /chat sans clé ``query`` dans le JSON -> 422 (Pydantic champ requis)."""
    resp = client.post("/chat", json={"session_id": "sess-x"})
    assert resp.status_code == 422


def test_chat_rejects_whitespace_only_query(client: TestClient) -> None:
    """POST /chat avec query blanchâtre (``'   '``) -> 422 (field_validator)."""
    resp = client.post("/chat", json={"query": "   \n\t  "})
    assert resp.status_code == 422
    # L'API n'invoque jamais l'agent pour un payload invalide.
    assert resp.json()["detail"][0]["msg"].startswith(
        "query ne peut pas être uniquement composée d'espaces"
    ) or any(
        "espaces" in err.get("msg", "")
        for err in resp.json()["detail"]
    )


# ---------------------------------------------------------------------------
# /chat : gestion du session_id
# ---------------------------------------------------------------------------


def test_chat_generates_uuid_when_session_id_empty(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """Si session_id est vide, l'API génère un UUID4 (36 chars) et le thread_id du checkpointer."""
    resp = client.post("/chat", json={"query": "Bonjour ?"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["session_id"]) == 36

    payload, config = fake_agent.invocations[-1]
    assert config is not None
    assert config["configurable"]["thread_id"] == body["session_id"]


def test_chat_preserves_explicit_session_id(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """Si session_id est fourni, l'API ne le modifie pas (ni en entrée, ni en checkpointer)."""
    resp = client.post("/chat", json={"query": "ping", "session_id": "sess-42"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-42"

    payload, config = fake_agent.invocations[-1]
    assert payload["session_id"] == "sess-42"
    assert config["configurable"]["thread_id"] == "sess-42"


def test_chat_treats_whitespace_only_session_id_as_empty(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """Un session_id uniquement composé d'espaces est considéré comme vide."""
    resp = client.post("/chat", json={"query": "ping", "session_id": "   "})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["session_id"]) == 36


# ---------------------------------------------------------------------------
# /chat : contrat avec l'agent
# ---------------------------------------------------------------------------


def test_chat_sends_human_message_to_agent(
    client: TestClient, fake_agent: FakeAgentApp
) -> None:
    """L'API envoie un HumanMessage (contenu = query) à l'agent, sans message supplémentaire."""
    resp = client.post("/chat", json={"query": "règles du snatch ?"})
    assert resp.status_code == 200

    payload, _ = fake_agent.invocations[-1]
    assert len(payload["messages"]) == 1
    msg = payload["messages"][0]
    assert isinstance(msg, HumanMessage)
    assert msg.content == "règles du snatch ?"


def test_chat_returns_agent_text_in_response(client: TestClient) -> None:
    """La réponse HTTP contient le contenu textuel produit par l'agent."""
    app = create_app()
    agent = FakeAgentApp(response="Voici l'Article 5.")
    app.dependency_overrides[get_agent_app] = lambda: agent

    with TestClient(app) as c:
        resp = c.post("/chat", json={"query": "?"})

    assert resp.status_code == 200
    assert resp.json()["response"] == "Voici l'Article 5."


# ---------------------------------------------------------------------------
# /chat : gestion d'erreurs
# ---------------------------------------------------------------------------


def test_chat_returns_500_when_agent_explodes(monkeypatch) -> None:
    """Une exception de l'agent devient un 500 sans fuite du message d'origine."""
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
    assert "Erreur interne" in resp.text


class SilentAgent:
    """Compilable LangGraph qui renvoie un état sans message (boucle avortée)."""

    def invoke(self, payload: dict, config: dict | None = None) -> dict:
        return {
            "messages": [],
            "retrieved_docs": [],
            "tool_calls": [],
            "session_id": payload.get("session_id", ""),
        }


def test_chat_returns_502_when_agent_yields_no_messages(monkeypatch) -> None:
    """Si l'agent renvoie ``messages: []``, l'API répond 502 (pas 500 IndexError)."""
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
    assert "aucune réponse" in resp.text


# ---------------------------------------------------------------------------
# Factory et configuration
# ---------------------------------------------------------------------------


def test_create_app_returns_distinct_instances() -> None:
    """Deux appels à create_app() produisent deux instances FastAPI distinctes (pas de singleton global)."""
    a = create_app()
    b = create_app()
    assert a is not b


def test_create_app_uses_settings_title_and_version() -> None:
    """Les métadonnées OpenAPI (title, version) viennent des Settings."""
    app = create_app()
    assert app.title == "IWF AI Hub API"
    assert app.version == "0.1.0"


def test_create_app_registers_expected_routes() -> None:
    """Les routes GET /health et POST /chat sont enregistrées sur l'application."""
    app = create_app()
    routes = {
        (r.path, tuple(sorted(r.methods)))  # type: ignore[attr-defined]
        for r in app.routes
        if hasattr(r, "methods")
    }
    assert ("/health", ("GET",)) in routes
    assert ("/chat", ("POST",)) in routes
