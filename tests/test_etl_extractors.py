"""Unit tests for DataExtractor and DataLoader classes (no network).

These tests do not need network connection — they use temporary
DuckDB files created via tmp_path. They cover branches not tested
by test_etl_ow.py (which needs network access for real extractions).
"""

from __future__ import annotations

import duckdb
import pytest


def test_data_extractor_is_abstract() -> None:
    """Checks that DataExtractor is an abstract class and cannot be instantiated."""
    from src.pipelines.extract_results import DataExtractor

    with pytest.raises(TypeError):
        DataExtractor()  # type: ignore[abstract]


def test_data_loader_with_event_id(tmp_path) -> None:
    """Checks that DataLoader.load_to_duckdb with event_id creates the raw_ table
    with the event_id column, and the operation is idempotent.
    """
    from pandas import DataFrame

    from src.pipelines.extract_results import DataLoader

    db_file = tmp_path / "test_event.duckdb"
    loader = DataLoader(str(db_file))

    df = DataFrame({"col_a": [10, 20], "col_b": ["x", "y"]})
    loader.load_to_duckdb(df, "event_test", event_id=42)

    conn = duckdb.connect(str(db_file))
    try:
        rows = conn.execute(
            "SELECT col_a, col_b, event_id FROM raw_event_test ORDER BY col_a"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0] == (10, "x", 42)
        assert rows[1] == (20, "y", 42)

        # Idempotence: re-insert the same event_id replaces
        loader.load_to_duckdb(df, "event_test", event_id=42)
        row = conn.execute("SELECT count(*) FROM raw_event_test").fetchone()
        assert row is not None
        count = row[0]
        assert count == 2

        # Different event_id appends
        df2 = DataFrame({"col_a": [30], "col_b": ["z"]})
        loader.load_to_duckdb(df2, "event_test", event_id=99)
        row = conn.execute("SELECT count(*) FROM raw_event_test").fetchone()
        assert row is not None
        count = row[0]
        assert count == 3
    finally:
        conn.close()


def test_data_loader_without_event_id(tmp_path) -> None:
    """Checks that DataLoader.load_to_duckdb without event_id uses CREATE OR REPLACE TABLE."""
    from pandas import DataFrame

    from src.pipelines.extract_results import DataLoader

    db_file = tmp_path / "test_no_event.duckdb"
    loader = DataLoader(str(db_file))

    df = DataFrame({"val": [1, 2, 3]})
    loader.load_to_duckdb(df, "no_event_test")

    conn = duckdb.connect(str(db_file))
    try:
        rows = conn.execute("SELECT val FROM raw_no_event_test ORDER BY val").fetchall()
        assert rows == [(1,), (2,), (3,)]

        # Re-insert replaces (CREATE OR REPLACE)
        df2 = DataFrame({"val": [99]})
        loader.load_to_duckdb(df2, "no_event_test")
        rows = conn.execute("SELECT val FROM raw_no_event_test").fetchall()
        assert rows == [(99,)]
    finally:
        conn.close()
