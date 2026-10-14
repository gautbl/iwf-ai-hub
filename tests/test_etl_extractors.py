"""Tests unitaires pour les classes DataExtractor et DataLoader (hors réseau).

Ces tests n'ont pas besoin de connexion réseau — ils utilisent des
fichiers DuckDB temporaires créés via tmp_path. Ils couvrent les
branches non testées par test_etl_ow.py (qui nécessite un accès
réseau pour les extractions réelles).
"""

from __future__ import annotations

import duckdb
import pytest


def test_data_extractor_is_abstract() -> None:
    """Vérifie que DataExtractor est une classe abstraite et ne peut pas être instanciée."""
    from src.pipelines.extract_results import DataExtractor

    with pytest.raises(TypeError):
        DataExtractor()  # type: ignore[abstract]


def test_data_loader_with_event_id(tmp_path) -> None:
    """Vérifie que DataLoader.load_to_duckdb avec event_id crée la table raw_
    avec la colonne event_id, et que l'opération est idempotente.
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

        # Idempotence : réinsérer le même event_id remplace
        loader.load_to_duckdb(df, "event_test", event_id=42)
        row = conn.execute("SELECT count(*) FROM raw_event_test").fetchone()
        assert row is not None
        count = row[0]
        assert count == 2

        # event_id différent s'ajoute
        df2 = DataFrame({"col_a": [30], "col_b": ["z"]})
        loader.load_to_duckdb(df2, "event_test", event_id=99)
        row = conn.execute("SELECT count(*) FROM raw_event_test").fetchone()
        assert row is not None
        count = row[0]
        assert count == 3
    finally:
        conn.close()


def test_data_loader_without_event_id(tmp_path) -> None:
    """Vérifie que DataLoader.load_to_duckdb sans event_id utilise CREATE OR REPLACE TABLE."""
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

        # Réinsérer remplace (CREATE OR REPLACE)
        df2 = DataFrame({"val": [99]})
        loader.load_to_duckdb(df2, "no_event_test")
        rows = conn.execute("SELECT val FROM raw_no_event_test").fetchall()
        assert rows == [(99,)]
    finally:
        conn.close()
