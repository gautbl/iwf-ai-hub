"""Tests de l'agent LangGraph IWF (Phase 4).

Conventions pytest-conventions : docstrings en français, variables en
anglais, aucun appel réseau ni Ollama réel — tout est vérifié localement.
"""

from typing import Annotated, get_args, get_origin, is_typeddict

from langgraph.graph.message import add_messages

from src.agent.state import AgentState


def test_agent_state_schema():
    """Vérifie que AgentState est un TypedDict exposant exactement les 4
    clés requises, avec le reducer add_messages sur messages et les bons
    types pour les autres champs.
    """
    # 1. TypedDict et clés exactes
    assert is_typeddict(AgentState)
    assert set(AgentState.__annotations__) == {
        "messages",
        "retrieved_docs",
        "tool_calls",
        "session_id",
    }

    # 2. messages : Annotated[list, add_messages] (reducer LangGraph)
    messages_annotation = AgentState.__annotations__["messages"]
    assert get_origin(messages_annotation) is Annotated
    base_type, reducer = get_args(messages_annotation)
    assert base_type is list
    assert reducer is add_messages

    # 3. Chunks et appels d'outils : list[dict]
    assert AgentState.__annotations__["retrieved_docs"] == list[dict]
    assert AgentState.__annotations__["tool_calls"] == list[dict]

    # 4. session_id : str
    assert AgentState.__annotations__["session_id"] is str


# ---------------------------------------------------------------------------
# Outils (ETAPE 3) — mock DuckDB, jamais la base de production
# ---------------------------------------------------------------------------


class FakeConnection:
    """Double de connexion DuckDB : capture SQL/params, renvoie des lignes fixes."""

    def __init__(
        self,
        columns: list[str],
        rows: list[tuple],
        error: Exception | None = None,
    ):
        self._columns = columns
        self._rows = rows
        self._error = error
        self.captured_sql: str | None = None
        self.captured_params: list | None = None
        self.read_only: bool | None = None
        self.closed: bool = False

    def execute(self, sql: str, params: list | None = None) -> "FakeConnection":
        if self._error is not None:
            raise self._error
        self.captured_sql = sql
        self.captured_params = params
        return self

    @property
    def description(self) -> list[tuple]:
        return [(name, None) for name in self._columns]

    def fetchall(self) -> list[tuple]:
        return self._rows

    def fetchone(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def close(self) -> None:
        self.closed = True


def _patch_connect(monkeypatch, connection: FakeConnection) -> None:
    """Remplace duckdb.connect dans src.agent.tools par une fausse connexion."""

    def fake_connect(path: str, read_only: bool = False) -> FakeConnection:
        connection.read_only = read_only
        return connection

    monkeypatch.setattr("src.agent.tools.duckdb.connect", fake_connect)


def test_search_regulations_delegates_to_retrieval(monkeypatch):
    """Vérifie que search_regulations délègue à retrieval.retrieve en
    transmettant la requête, le chemin de base et top_k tels quels.
    """
    from src.agent import tools

    captured = {}

    def fake_retrieve(query: str, db_path: str, top_k: int = 5) -> list[dict]:
        captured["query"] = query
        captured["db_path"] = db_path
        captured["top_k"] = top_k
        return [
            {
                "chunk_text": "Article 5",
                "source": "tcrr.pdf",
                "article": "Article 5",
                "page": 12,
                "score": 0.91,
            }
        ]

    monkeypatch.setattr(tools.retrieval, "retrieve", fake_retrieve)

    docs = tools.search_regulations("clean and jerk rules", top_k=3)

    assert captured == {
        "query": "clean and jerk rules",
        "db_path": tools.DB_PATH,
        "top_k": 3,
    }
    assert len(docs) == 1
    assert docs[0]["chunk_text"] == "Article 5"


def test_search_regulations_db_error_returns_empty(monkeypatch):
    """Vérifie la dégradation : une erreur DuckDB renvoie une liste vide."""
    import duckdb as duckdb_module

    from src.agent import tools

    def fake_retrieve(query: str, db_path: str, top_k: int = 5) -> list[dict]:
        raise duckdb_module.Error("db unavailable")

    monkeypatch.setattr(tools.retrieval, "retrieve", fake_retrieve)

    assert tools.search_regulations("query") == []


def test_query_results_applies_dynamic_filters(monkeypatch):
    """Vérifie les filtres dynamiques : conditions ET, ILIKE insensible à
    la casse, filtre de date casté en VARCHAR, ordre des paramètres.
    """
    from src.agent import tools

    columns = [
        "athlete_name",
        "category_name",
        "event_date",
        "snatch_total",
        "clean_jerk_total",
        "combined_total",
    ]
    conn = FakeConnection(
        columns, [("LU Xiaojun", "77 kg Men", "2021-07-28", 170.0, 207.0, 377.0)]
    )
    _patch_connect(monkeypatch, conn)

    rows = tools.query_results(
        athlete_name="lu xiaojun",
        category_name="77 kg Men",
        event_date="2021-07-28",
    )

    assert conn.read_only is True
    assert conn.captured_sql.count("JOIN") == 2
    assert conn.captured_sql.count("ILIKE ?") == 2
    assert "CAST(f.event_date AS VARCHAR) = ?" in conn.captured_sql
    assert conn.captured_params == ["lu xiaojun", "77 kg Men", "2021-07-28"]
    assert rows[0]["athlete_name"] == "LU Xiaojun"
    assert rows[0]["combined_total"] == 377.0
    assert conn.closed is True


def test_query_results_without_filters(monkeypatch):
    """Vérifie qu'aucun filtre ne génère de clause WHERE ni de paramètre."""
    from src.agent import tools

    columns = ["athlete_name", "category_name", "event_date"]
    conn = FakeConnection(columns, [])
    _patch_connect(monkeypatch, conn)

    rows = tools.query_results()

    assert "WHERE" not in conn.captured_sql
    assert conn.captured_params is None
    assert rows == []


def test_query_results_connect_error_returns_empty(monkeypatch):
    """Vérifie la dégradation : base DuckDB absente ou illisible -> []."""
    import duckdb as duckdb_module

    from src.agent import tools

    def broken_connect(path: str, read_only: bool = False) -> FakeConnection:
        raise duckdb_module.IOException("cannot open database")

    monkeypatch.setattr("src.agent.tools.duckdb.connect", broken_connect)

    assert tools.query_results(athlete_name="X") == []


def test_compute_athlete_stats_found(monkeypatch):
    """Vérifie les agrégats renvoyés pour un athlète présent en base."""
    from src.agent import tools

    columns = [
        "athlete_name",
        "best_snatch",
        "best_clean_jerk",
        "best_total",
        "nb_competitions",
    ]
    conn = FakeConnection(columns, [("LU Xiaojun", 170.0, 207.0, 377.0, 12)])
    _patch_connect(monkeypatch, conn)

    stats = tools.compute_athlete_stats("lu xiaojun")

    assert "ILIKE ?" in conn.captured_sql
    assert conn.captured_params == ["lu xiaojun"]
    assert stats == {
        "athlete_name": "LU Xiaojun",
        "best_snatch": 170.0,
        "best_clean_jerk": 207.0,
        "best_total": 377.0,
        "nb_competitions": 12,
    }


def test_compute_athlete_stats_unknown_athlete(monkeypatch):
    """Vérifie qu'un athlète introuvable renvoie un dict vide."""
    from src.agent import tools

    columns = ["athlete_name", "best_snatch", "best_clean_jerk", "best_total", "nb_competitions"]
    conn = FakeConnection(columns, [])
    _patch_connect(monkeypatch, conn)

    assert tools.compute_athlete_stats("athlete inconnu") == {}
    assert conn.closed is True


def test_compute_athlete_stats_db_error_returns_empty(monkeypatch):
    """Vérifie la dégradation : une erreur DuckDB renvoie un dict vide."""
    import duckdb as duckdb_module

    from src.agent import tools

    def broken_connect(path: str, read_only: bool = False) -> FakeConnection:
        raise duckdb_module.IOException("cannot open database")

    monkeypatch.setattr("src.agent.tools.duckdb.connect", broken_connect)

    assert tools.compute_athlete_stats("X") == {}


def test_search_regulations_unexpected_error_returns_empty(monkeypatch):
    """Vérifie la dégradation : une exception inattendue (ex: KeyError
    d'un embedding Ollama malformé) renvoie une liste vide sans jamais
    remonter vers le tool_node."""
    from src.agent import tools

    def fake_retrieve(query: str, db_path: str, top_k: int = 5) -> list[dict]:
        raise KeyError("embedding")

    monkeypatch.setattr(tools.retrieval, "retrieve", fake_retrieve)

    assert tools.search_regulations("query") == []


def test_query_results_escapes_like_wildcards(monkeypatch):
    """Vérifie que les caractères génériques LIKE (%, _) sont échappés
    dans les filtres athlete_name et category_name, et que la clause
    ESCAPE est bien présente dans le SQL généré."""
    from src.agent import tools

    columns = ["athlete_name", "category_name", "event_date"]
    conn = FakeConnection(columns, [])
    _patch_connect(monkeypatch, conn)

    rows = tools.query_results(athlete_name="A_1%", category_name="77_kg")

    assert conn.captured_params == ["A\\_1\\%", "77\\_kg"]
    assert "ESCAPE" in conn.captured_sql
    assert rows == []


def test_compute_athlete_stats_wildcards_do_not_match(tmp_path, monkeypatch):
    """Vérifie la sémantique ESCAPE de bout en bout sur une vraie base
    DuckDB : '_' échappé ne matche pas n'importe quel caractère, donc
    'A_1' ne renvoie que la ligne de A_1 et pas celle de AB1."""
    import duckdb as duckdb_module

    from src.agent import tools

    db_file = tmp_path / "agent_escape_test.duckdb"
    conn = duckdb_module.connect(str(db_file))
    conn.execute("CREATE TABLE dim_athletes (athlete_id INTEGER, name VARCHAR)")
    conn.execute(
        "CREATE TABLE dim_weight_classes (class_id INTEGER, category_name VARCHAR)"
    )
    conn.execute(
        "CREATE TABLE fct_results (athlete_id INTEGER, class_id INTEGER, "
        "event_date DATE, snatch_total DOUBLE, clean_jerk_total DOUBLE, "
        "combined_total DOUBLE)"
    )
    conn.execute("INSERT INTO dim_athletes VALUES (1, 'A_1'), (2, 'AB1')")
    conn.execute("INSERT INTO dim_weight_classes VALUES (1, '77 kg Men')")
    conn.execute(
        "INSERT INTO fct_results VALUES "
        "(1, 1, DATE '2021-07-28', 170.0, 207.0, 377.0), "
        "(2, 1, DATE '2021-07-28', 160.0, 200.0, 360.0)"
    )
    conn.close()

    monkeypatch.setattr(tools, "DB_PATH", str(db_file))

    stats = tools.compute_athlete_stats("A_1")

    assert stats["athlete_name"] == "A_1"
    assert stats["nb_competitions"] == 1
    assert stats["best_total"] == 377.0


# ---------------------------------------------------------------------------
# Graphe (ETAPE 4) — LLM et retrieval mockés, jamais d'Ollama réel
# ---------------------------------------------------------------------------

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.agent import graph


class FakeBoundLLM:
    """Double de ChatOllama.bind_tools : capture les messages reçus et
    renvoie une réponse AIMessage fixe (jamais de tool_calls, pour que le
    graphe ne puisse pas boucler agent -> tools)."""

    def __init__(self, response: AIMessage):
        self._response = response
        self.invoked_messages: list | None = None

    def invoke(self, messages: list) -> AIMessage:
        self.invoked_messages = messages
        return self._response


class FakeChatOllama:
    """Double de ChatOllama : bind_tools renvoie un FakeBoundLLM."""

    def __init__(self, response: AIMessage):
        self._response = response
        self.bound_tools: list | None = None

    def bind_tools(self, tools: list) -> FakeBoundLLM:
        self.bound_tools = tools
        return FakeBoundLLM(self._response)


def test_retrieve_node(monkeypatch):
    """Vérifie que retrieve_node délègue à tools.search_regulations et
    expose les chunks récupérés dans retrieved_docs."""
    docs = [
        {
            "chunk_text": "Article 5",
            "source": "tcrr.pdf",
            "article": "Article 5",
            "page": 12,
            "score": 0.91,
        },
        {
            "chunk_text": "Article 6",
            "source": "tcrr.pdf",
            "article": "Article 6",
            "page": 13,
            "score": 0.80,
        },
    ]

    def fake_search(query: str, top_k: int = 5) -> list[dict]:
        return docs

    monkeypatch.setattr("src.agent.tools.search_regulations", fake_search)

    result = graph.retrieve_node({"messages": [HumanMessage(content="q")]})

    assert result == {"retrieved_docs": docs}


def test_agent_node(monkeypatch):
    """Vérifie que agent_node injecte le contexte réglementaire en
    SystemMessage en tête des messages et renvoie la réponse du LLM mocké."""
    fake = FakeChatOllama(AIMessage(content="réponse", tool_calls=[]))
    bound = fake.bind_tools([])
    monkeypatch.setattr(graph, "ChatOllama", fake)
    monkeypatch.setattr(graph, "_bound_llm", bound)

    state = {
        "messages": [HumanMessage(content="quelles sont les règles ?")],
        "retrieved_docs": [
            {
                "chunk_text": "Article 5",
                "source": "tcrr.pdf",
                "article": "Article 5",
                "page": 12,
            }
        ],
        "tool_calls": [],
        "session_id": "s1",
    }

    result = graph.agent_node(state)

    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == "réponse"
    # le premier message transmis au LLM est le SystemMessage de contexte
    assert isinstance(bound.invoked_messages[0], SystemMessage)
    assert "Article 5" in bound.invoked_messages[0].content
    assert isinstance(bound.invoked_messages[1], HumanMessage)


def test_tool_node(monkeypatch):
    """Vérifie que tool_node dispatche les tool_calls vers tools.TOOLS et
    produit un ToolMessage JSON par appel, avec l'appel enregistré dans
    tool_calls."""
    def stub(athlete_name: str) -> dict:
        return {"athlete_name": athlete_name, "best_total": 377.0}

    monkeypatch.setattr("src.agent.tools.TOOLS", {"compute_athlete_stats": stub})

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "compute_athlete_stats",
                        "args": {"athlete_name": "X"},
                        "id": "call_1",
                    }
                ],
            )
        ],
        "retrieved_docs": [],
        "tool_calls": [],
        "session_id": "s1",
    }

    result = graph.tool_node(state)

    assert len(result["messages"]) == 1
    tool_message = result["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.tool_call_id == "call_1"
    assert json.loads(tool_message.content) == {
        "athlete_name": "X",
        "best_total": 377.0,
    }
    assert result["tool_calls"] == [
        {
            "name": "compute_athlete_stats",
            "args": {"athlete_name": "X"},
            "id": "call_1",
            "type": "tool_call",
        }
    ]


def test_tool_node_dispatch_error(monkeypatch):
    """Vérifie la dégradation : une exception d'outil produit un ToolMessage
    {"error": ...} sans jamais remonter vers le graphe."""
    def broken(athlete_name: str) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr("src.agent.tools.TOOLS", {"compute_athlete_stats": broken})

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "compute_athlete_stats",
                        "args": {"athlete_name": "X"},
                        "id": "call_1",
                    }
                ],
            )
        ],
        "retrieved_docs": [],
        "tool_calls": [],
        "session_id": "s1",
    }

    result = graph.tool_node(state)

    tool_message = result["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert "error" in json.loads(tool_message.content)


def test_graph_integration(monkeypatch):
    """Test d'intégration du graphe complet sur la base de test DuckDB :
    LLM mocké (jamais de tool_calls), retrieval mocké, checkpointer réel.
    Nettoie les tables de checkpoints de la base de test en fin de test."""
    import duckdb as duckdb_module

    db_path = "data/duckdb/test_iwf_hub.duckdb"

    fake = FakeChatOllama(AIMessage(content="réponse finale", tool_calls=[]))
    # build_graph instancie ChatOllama(...) : on patche avec un callable
    # qui renvoie l'instance factice pré-construite.
    monkeypatch.setattr(graph, "ChatOllama", lambda **kwargs: fake)

    def fake_search(query: str, top_k: int = 5) -> list[dict]:
        return [
            {
                "chunk_text": "Article 5",
                "source": "tcrr.pdf",
                "article": "Article 5",
                "page": 12,
                "score": 0.91,
            }
        ]

    monkeypatch.setattr("src.agent.tools.search_regulations", fake_search)
    monkeypatch.setattr(graph, "_app", graph.build_graph(db_path=db_path))

    try:
        result = graph.run("quelles sont les règles ?", "test-session")
        assert result == "réponse finale"
    finally:
        conn = duckdb_module.connect(db_path)
        for table in (
            "checkpoints",
            "checkpoint_blobs",
            "checkpoint_migrations",
            "checkpoint_writes",
        ):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.close()
