"""Tools for the IWF agent (Phase 4).

Three tools exposed to the LangGraph graph:
- search_regulations: vector search in regulations (VSS)
- query_results: queries the Star Schema (fct_results + dimensions)
- compute_athlete_stats: performance aggregates per athlete

All DuckDB access is read-only and degrades cleanly
(empty list / empty dict + structlog log) if the DB is unavailable,
so a tool failure never crashes the graph.
"""

import os
from collections.abc import Callable

import duckdb
import structlog

from src.pipelines import retrieval

logger = structlog.get_logger()

# Project DuckDB path (production). Tools only read from it.
DB_PATH = os.environ.get("IWF_DUCKDB_PATH", "data/duckdb/iwf_hub.duckdb")


def _escape_like(value: str) -> str:
    """Escapes LIKE wildcard characters (%, _) and the escape char."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_regulations(query: str, top_k: int = 5) -> list[dict]:
    """Searches for regulation snippets closest to a query.

    Delegates to Phase 3 VSS retrieval (embed the query via
    local Ollama, cosine similarity on the chunks table).

    Args:
        query: natural language question about IWF regulations.
        top_k: maximum number of snippets to return.

    Returns:
        List of dicts {chunk_text, source, article, page, score}, sorted
        by descending score. Empty list if Ollama or DuckDB is
        unavailable, or on unexpected error: the tool is the graph
        error boundary, no exception must reach the tool_node.
    """
    try:
        return retrieval.retrieve(query, DB_PATH, top_k)
    except duckdb.Error as exc:
        logger.error("search_regulations_db_error", error=str(exc))
        return []
    except Exception as exc:
        logger.error("search_regulations_unexpected_error", error=str(exc))
        return []


def query_results(
    athlete_name: str | None = None,
    category_name: str | None = None,
    event_date: str | None = None,
) -> list[dict]:
    """Queries the Star Schema: results filtered by athlete, category or date.

    Filters combine with AND and only non-null parameters generate
    a condition. Name comparisons are case-insensitive (ILIKE) and
    LIKE wildcard chars (%, _) are escaped to prevent accidental matches.

    Args:
        athlete_name: athlete name, or None.
        category_name: weight category (e.g. "77 kg Men"), or None.
        event_date: competition date as "YYYY-MM-DD", or None.

    Returns:
        List of dicts {athlete_name, category_name, event_date,
        snatch_total, clean_jerk_total, combined_total}. Empty list if
        the DB is unavailable or no row matches.
    """
    conditions: list[str] = []
    params: list[str] = []
    if athlete_name is not None:
        conditions.append("a.name ILIKE ? ESCAPE '\\'")
        params.append(_escape_like(athlete_name))
    if category_name is not None:
        conditions.append("wc.category_name ILIKE ? ESCAPE '\\'")
        params.append(_escape_like(category_name))
    if event_date is not None:
        conditions.append("CAST(f.event_date AS VARCHAR) = ?")
        params.append(event_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT a.name AS athlete_name,
               wc.category_name AS category_name,
               f.event_date AS event_date,
               f.snatch_total AS snatch_total,
               f.clean_jerk_total AS clean_jerk_total,
               f.combined_total AS combined_total
        FROM fct_results f
        JOIN dim_athletes a ON f.athlete_id = a.athlete_id
        JOIN dim_weight_classes wc ON f.class_id = wc.class_id
        {where_clause}
    """

    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
    except duckdb.Error as exc:
        logger.error("query_results_connect_error", error=str(exc))
        return []

    try:
        conn.execute(sql, params if params else None)
        columns = [col[0] for col in conn.description]
        rows = conn.fetchall()
        return [dict(zip(columns, row, strict=False)) for row in rows]
    except duckdb.Error as exc:
        logger.error("query_results_query_error", error=str(exc))
        return []
    finally:
        conn.close()


def compute_athlete_stats(athlete_name: str) -> dict:
    """Calculates the best results for an athlete from the fact table.

    Args:
        athlete_name: athlete name (case-insensitive match,
            LIKE wildcard chars escaped).

    Returns:
        Dict {athlete_name, best_snatch, best_clean_jerk, best_total,
        nb_competitions}. Empty dict if athlete not found or
        the DB is unavailable.
    """
    sql = """
        SELECT a.name AS athlete_name,
               MAX(f.snatch_total) AS best_snatch,
               MAX(f.clean_jerk_total) AS best_clean_jerk,
               MAX(f.combined_total) AS best_total,
               COUNT(*) AS nb_competitions
        FROM fct_results f
        JOIN dim_athletes a ON f.athlete_id = a.athlete_id
        WHERE a.name ILIKE ? ESCAPE '\\'
        GROUP BY a.name
    """

    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
    except duckdb.Error as exc:
        logger.error("compute_athlete_stats_connect_error", error=str(exc))
        return {}

    try:
        conn.execute(sql, [_escape_like(athlete_name)])
        row = conn.fetchone()
        if row is None:
            logger.info("athlete_not_found", athlete_name=athlete_name)
            return {}
        columns = [col[0] for col in conn.description]
        return dict(zip(columns, row, strict=False))
    except duckdb.Error as exc:
        logger.error("compute_athlete_stats_query_error", error=str(exc))
        return {}
    finally:
        conn.close()


# Dispatch registry for the graph tool_node (tool name -> function).
TOOLS: dict[str, Callable[..., list[dict] | dict]] = {
    "search_regulations": search_regulations,
    "query_results": query_results,
    "compute_athlete_stats": compute_athlete_stats,
}
