import os

import pytest

from src.pipelines.load_pdfs import load_pdfs


def test_load_pdfs_success(tmp_path):
    """
    Test that PDFs are correctly loaded and text is extracted.
    """
    # 1. Setup: Create a temporary PDF for testing
    # Note: In a real scenario, you'd use a small sample PDF from your data/pdfs folder
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "test_rules.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "IWF Rule 1: Clean and Jerk must be performed.")
    c.save()

    pdf_folder = tmp_path

    # 2. Execute
    docs = load_pdfs(str(pdf_folder))

    # 3. Assert
    assert len(docs) == 1
    assert "IWF Rule 1" in docs[0]["text"]
    assert docs[0]["metadata"]["source"] == "test_rules.pdf"
    assert docs[0]["metadata"]["page"] == 1


def test_chunk_output_schema(tmp_path):
    """
    Checks that each chunk exposes the 5 required fields with the correct types.
    """
    from reportlab.pdfgen import canvas

    from src.pipelines.chunking import JuridicalChunker

    # 1. Setup: PDF temporaire avec un article IWF
    pdf_path = tmp_path / "test_articles.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Article 5 - Clean and Jerk must be performed.")
    c.save()

    docs = load_pdfs(str(tmp_path))
    assert len(docs) == 1

    # 2. Execute
    chunker = JuridicalChunker(chunk_size=64, chunk_overlap=8)
    chunks = chunker.chunk_text(
        docs[0]["text"],
        source=docs[0]["metadata"]["source"],
        page=docs[0]["metadata"]["page"],
    )

    # 3. Assert
    assert len(chunks) >= 1
    for chunk in chunks:
        assert set(chunk.keys()) == {"id", "source", "article", "page", "chunk_text"}
        assert isinstance(chunk["id"], str)
        assert isinstance(chunk["source"], str)
        assert chunk["article"] is None or isinstance(chunk["article"], str)
        assert isinstance(chunk["page"], int)
        assert isinstance(chunk["chunk_text"], str)

    assert chunks[0]["source"] == "test_articles.pdf"
    assert chunks[0]["page"] == 1


def test_chunk_article_detection(tmp_path):
    """
    Checks the isolation of article detection: a chunk containing
    "Article 5" exposes "Article 5" in its article field.
    """
    from reportlab.pdfgen import canvas

    from src.pipelines.chunking import JuridicalChunker

    # 1. Setup: PDF temporaire avec un article IWF
    pdf_path = tmp_path / "test_article_detection.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Article 5 - Clean and Jerk must be performed.")
    c.save()

    docs = load_pdfs(str(tmp_path))
    assert len(docs) == 1

    # 2. Execute
    chunker = JuridicalChunker(chunk_size=64, chunk_overlap=8)
    chunks = chunker.chunk_text(
        docs[0]["text"],
        source=docs[0]["metadata"]["source"],
        page=docs[0]["metadata"]["page"],
    )

    # 3. Assert: article detection only
    assert len(chunks) >= 1
    assert chunks[0]["article"] == "Article 5"


def test_embed_calls_ollama_local(monkeypatch):
    """
    Checks that embed_text calls the local Ollama API with the correct
    endpoint, body and timeout.
    """
    from src.pipelines.embeddings import EmbeddingGenerator

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"embedding": [0.0] * 768}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("src.pipelines.embeddings.requests.post", fake_post)

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path="unused.duckdb"
    )
    vector = generator.embed_text("Article 5")

    assert len(vector) == 768
    assert captured["url"] == "http://localhost:11434/api/embeddings"
    assert captured["json"] == {"model": "nomic-embed-text", "prompt": "Article 5"}
    assert captured["timeout"] == 30


def test_embed_dimension_error(monkeypatch):
    """
    Checks that a vector of dimension 384 raises a ValueError.
    """
    from src.pipelines.embeddings import EmbeddingGenerator

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"embedding": [0.0] * 384}

    monkeypatch.setattr(
        "src.pipelines.embeddings.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path="unused.duckdb"
    )
    with pytest.raises(ValueError):
        generator.embed_text("Article 5")


def test_embed_connection_error(monkeypatch):
    """
    Checks that a ConnectionError to Ollama is propagated.
    """
    import requests

    from src.pipelines.embeddings import EmbeddingGenerator

    def raise_connection_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError("Ollama indisponible")

    monkeypatch.setattr(
        "src.pipelines.embeddings.requests.post", raise_connection_error
    )

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path="unused.duckdb"
    )
    with pytest.raises(requests.exceptions.ConnectionError):
        generator.embed_text("Article 5")


def test_embed_timeout(monkeypatch):
    """
    Checks that an Ollama Timeout is logged then propagated.
    """
    import requests

    from src.pipelines.embeddings import EmbeddingGenerator

    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout("Ollama timeout")

    monkeypatch.setattr("src.pipelines.embeddings.requests.post", raise_timeout)

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path="unused.duckdb"
    )
    with pytest.raises(requests.exceptions.Timeout):
        generator.embed_text("Article 5")


def test_embed_http_error(monkeypatch):
    """
    Checks that an HTTP 500 response triggers a RuntimeError.
    """
    from src.pipelines.embeddings import EmbeddingGenerator

    class FakeResponse:
        status_code = 500

        def json(self):
            return {}

    monkeypatch.setattr(
        "src.pipelines.embeddings.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path="unused.duckdb"
    )
    with pytest.raises(RuntimeError):
        generator.embed_text("Article 5")


def test_retrieve_returns_list(monkeypatch):
    """
    Checks the return type and presented fields in each result.
    """
    from src.pipelines import retrieval

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            return [0.0] * 768

    class FakeConnection:
        def __init__(self, rows):
            self._rows = rows

        def execute(self, sql, params=None):
            return self

        def fetchall(self):
            return self._rows

        def close(self):
            pass

    rows = [
        ("chunk A", "iwf.pdf", "Article 5", 3, 0.99),
        ("chunk B", "iwf.pdf", None, 4, 0.80),
    ]

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)
    monkeypatch.setattr(
        retrieval.duckdb, "connect", lambda db_path: FakeConnection(rows)
    )

    results = retrieval.retrieve("clean and jerk", db_path="unused.duckdb", top_k=5)

    assert isinstance(results, list)
    assert len(results) == 2
    for result in results:
        assert set(result.keys()) == {
            "chunk_text",
            "source",
            "article",
            "page",
            "score",
        }
    assert results[0]["chunk_text"] == "chunk A"
    assert results[0]["score"] == 0.99


def test_retrieve_top_k(monkeypatch):
    """
    Checks that top_k is correctly passed to the SQL query (LIMIT).
    """
    from src.pipelines import retrieval

    captured = {}

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            return [0.0] * 768

    class FakeConnection:
        def execute(self, sql, params=None):
            captured["sql"] = sql
            captured["params"] = params
            return self

        def fetchall(self):
            return []

        def close(self):
            pass

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)
    monkeypatch.setattr(retrieval.duckdb, "connect", lambda db_path: FakeConnection())

    retrieval.retrieve("query", db_path="unused.duckdb", top_k=3)

    assert "LIMIT" in captured["sql"].upper()
    assert captured["params"][-1] == 3


def test_retrieve_ollama_unavailable(monkeypatch):
    """
    Checks the degraded behaviour: Ollama unavailable => empty list.
    """
    import requests

    from src.pipelines import retrieval

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            raise requests.exceptions.ConnectionError("Ollama indisponible")

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)

    results = retrieval.retrieve("query", db_path="unused.duckdb", top_k=5)

    assert results == []


def test_retrieve_runtime_error(monkeypatch):
    """
    Checks the degraded behaviour: a RuntimeError (e.g. DuckDB connection)
    is intercepted and retrieve() returns an empty list.
    """
    from src.pipelines import retrieval

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            return [0.0] * 768

    def raise_runtime_error(db_path):
        raise RuntimeError("DuckDB indisponible")

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)
    monkeypatch.setattr(retrieval.duckdb, "connect", raise_runtime_error)

    results = retrieval.retrieve("query", db_path="unused.duckdb", top_k=5)

    assert results == []


def test_retrieve_value_error(monkeypatch):
    """
    Checks the degraded behaviour: a ValueError (e.g. invalid embedding)
    is intercepted and retrieve() returns an empty list.
    """
    from src.pipelines import retrieval

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            return [0.0] * 768

    def raise_value_error(db_path):
        raise ValueError("Dimension inattendue")

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)
    monkeypatch.setattr(retrieval.duckdb, "connect", raise_value_error)

    results = retrieval.retrieve("query", db_path="unused.duckdb", top_k=5)

    assert results == []


def test_load_pdf_extracts_text(tmp_path):
    """
    Checks text extraction and page number on a multi-page PDF.
    """
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "test_multipage.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Page one content")
    c.showPage()
    c.drawString(100, 750, "Page two content")
    c.save()

    docs = load_pdfs(str(tmp_path))

    assert len(docs) == 2
    pages = {doc["metadata"]["page"]: doc["text"] for doc in docs}
    assert "Page one content" in pages[1]
    assert "Page two content" in pages[2]


def test_load_pdf_file_not_found():
    """
    Checks that a non-existent directory raises a FileNotFoundError.
    """
    with pytest.raises(FileNotFoundError):
        load_pdfs("this/folder/does/not/exist")


@pytest.fixture
def rag_test_db():
    """
    Sets up the chunks table in the test DB and cleans up after.
    """
    import duckdb

    db_path = "data/duckdb/test_iwf_hub.duckdb"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with open("src/db/init.sql", encoding="utf-8") as f:
        init_sql = f.read()

    conn = duckdb.connect(db_path)
    conn.execute(init_sql)
    conn.execute("DELETE FROM chunks")
    conn.close()

    yield db_path

    conn = duckdb.connect(db_path)
    conn.execute("INSTALL vss;")
    conn.execute("LOAD vss;")
    conn.execute("DROP TABLE IF EXISTS chunks")
    conn.close()


def test_pipeline_integration(tmp_path, monkeypatch, rag_test_db):
    """
    Full pipeline load -> chunk -> embed -> store with mocked Ollama and
    verification of stored content in DuckDB.
    """
    import duckdb
    from reportlab.pdfgen import canvas

    from src.pipelines.chunking import JuridicalChunker
    from src.pipelines.embeddings import EmbeddingGenerator

    # 1. Test PDF generated with reportlab
    pdf_path = tmp_path / "iwf_rules.pdf"
    c = canvas.Canvas(str(pdf_path))
    c.drawString(100, 750, "Article 5 - Clean and Jerk must be performed.")
    c.save()

    # 2. Mock Ollama (never a real instance)
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"embedding": [0.01] * 768}

    monkeypatch.setattr(
        "src.pipelines.embeddings.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    # 3. load -> chunk
    docs = load_pdfs(str(tmp_path))
    assert len(docs) == 1

    chunker = JuridicalChunker(chunk_size=64, chunk_overlap=8)
    chunks = []
    for doc in docs:
        chunks.extend(
            chunker.chunk_text(
                doc["text"],
                source=doc["metadata"]["source"],
                page=doc["metadata"]["page"],
            )
        )
    assert len(chunks) >= 1

    # 4. embed -> store
    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path=rag_test_db
    )
    inserted = generator.store_chunks(chunks)
    assert inserted == len(chunks)

    # 5. DB verification
    conn = duckdb.connect(rag_test_db)
    conn.execute("INSTALL vss;")
    conn.execute("LOAD vss;")
    count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    row = conn.execute("SELECT source, article, page FROM chunks LIMIT 1").fetchone()
    conn.close()

    assert count == len(chunks)
    assert row[0] == "iwf_rules.pdf"
    assert row[1] == "Article 5"
    assert row[2] == 1


def test_embed_idempotence(monkeypatch, rag_test_db):
    """
    Checks that store_chunks is idempotent: re-inserting the same chunk id
    does not create a duplicate in the DB.
    """
    from uuid import uuid4

    import duckdb

    from src.pipelines.embeddings import EmbeddingGenerator

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"embedding": [0.0] * 768}

    monkeypatch.setattr(
        "src.pipelines.embeddings.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    chunk = {
        "id": str(uuid4()),
        "source": "iwf_rules.pdf",
        "article": "Article 5",
        "page": 1,
        "chunk_text": "Article 5 - Clean and Jerk must be performed.",
    }

    generator = EmbeddingGenerator(
        ollama_url="http://localhost:11434", db_path=rag_test_db
    )

    first_inserted = generator.store_chunks([chunk])
    second_inserted = generator.store_chunks([chunk])

    conn = duckdb.connect(rag_test_db)
    conn.execute("INSTALL vss;")
    conn.execute("LOAD vss;")
    count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    conn.close()

    assert first_inserted == 1
    assert second_inserted == 0
    assert count == 1


def test_retrieve_duckdb_error_is_re_raised(monkeypatch) -> None:
    """Checks that retrieve() lets a duckdb.Error propagate (the agent
    layer catches it)."""
    import duckdb as duckdb_module

    from src.pipelines import retrieval

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            return [0.0] * 768

    class FakeConn:
        def execute(self, sql, params=None):
            raise duckdb_module.Error("base corrompue")

        def close(self):
            pass

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)
    monkeypatch.setattr(retrieval.duckdb, "connect", lambda db_path: FakeConn())

    with pytest.raises(duckdb_module.Error):
        retrieval.retrieve("query", db_path="unused.duckdb", top_k=5)


@pytest.mark.parametrize(
    ("embed_error", "query_error"),
    [
        pytest.param(
            RuntimeError("Ollama returned HTTP 500"), None, id="runtime_on_embed"
        ),
        pytest.param(
            ValueError("Dimension inattendue : 384"), None, id="value_on_embed"
        ),
        pytest.param(None, RuntimeError("HNSW index corrompu"), id="runtime_on_query"),
        pytest.param(None, ValueError("dimension mismatch"), id="value_on_query"),
    ],
)
def test_retrieve_returns_empty_on_error(
    monkeypatch, embed_error: Exception | None, query_error: Exception | None
) -> None:
    """Checks the degraded behaviour: RuntimeError or ValueError during
    embed_text or the DuckDB query returns an empty list."""
    from src.pipelines import retrieval

    class FakeGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def embed_text(self, text):
            if embed_error is not None:
                raise embed_error
            return [0.0] * 768

    class FakeConn:
        def execute(self, sql, params=None):
            if query_error is not None:
                raise query_error
            return self

        def fetchall(self):
            return []

        def close(self):
            pass

    monkeypatch.setattr(retrieval, "EmbeddingGenerator", FakeGenerator)
    if query_error is not None:
        monkeypatch.setattr(retrieval.duckdb, "connect", lambda db_path: FakeConn())

    results = retrieval.retrieve("query", db_path="unused.duckdb", top_k=5)
    assert results == []
