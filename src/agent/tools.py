"""Outils de l'agent IWF (Phase 4).

Trois outils exposés au graphe LangGraph :
- search_regulations : recherche vectorielle dans les réglementations (VSS) ;
- query_results : interrogation du Star Schema (fct_results + dimensions) ;
- compute_athlete_stats : agrégats de performance par athlète.

Tous les accès DuckDB sont en lecture seule et dégradent proprement
(liste vide / dict vide + log structlog) si la base est indisponible,
de sorte qu'un échec d'outil ne fait jamais planter le graphe.
"""

from typing import Callable

import duckdb
import structlog

from src.pipelines import retrieval

logger = structlog.get_logger()

# Base DuckDB du projet (production). Les outils n'y font que des lectures.
DB_PATH = "data/duckdb/iwf_hub.duckdb"


def _escape_like(value: str) -> str:
    """Échappe les caractères génériques LIKE (%, _) et le caractère d'échappement."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_regulations(query: str, top_k: int = 5) -> list[dict]:
    """Recherche les extraits réglementaires les plus proches d'une requête.

    Délègue au retrieval VSS de la Phase 3 (embedding de la requête via
    Ollama local, similarité cosinus sur la table chunks).

    Args:
        query: question en langage naturel sur les réglementations IWF.
        top_k: nombre maximum d'extraits retournés.

    Returns:
        Liste de dicts {chunk_text, source, article, page, score}, triée
        par score décroissant. Liste vide si Ollama ou DuckDB est
        indisponible, ou en cas d'erreur inattendue : l'outil est la
        frontière d'erreur du graphe, aucune exception ne doit remonter
        vers le tool_node.
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
    """Interroge le Star Schema : résultats filtrés par athlète, catégorie ou date.

    Les filtres sont combinés par ET et seuls les paramètres non nuls
    génèrent une condition. Les comparaisons de noms sont insensibles
    à la casse (ILIKE) et les caractères génériques LIKE (%, _) sont
    échappés pour éviter les correspondances accidentelles.

    Args:
        athlete_name: nom de l'athlète, sinon None.
        category_name: catégorie de poids (ex: "77 kg Men"), sinon None.
        event_date: date de compétition au format "YYYY-MM-DD", sinon None.

    Returns:
        Liste de dicts {athlete_name, category_name, event_date,
        snatch_total, clean_jerk_total, combined_total}. Liste vide si
        la base est indisponible ou si aucune ligne ne correspond.
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
        return [dict(zip(columns, row)) for row in rows]
    except duckdb.Error as exc:
        logger.error("query_results_query_error", error=str(exc))
        return []
    finally:
        conn.close()


def compute_athlete_stats(athlete_name: str) -> dict:
    """Calcule les meilleurs résultats d'un athlète à partir de la table de faits.

    Args:
        athlete_name: nom de l'athlète (comparaison insensible à la casse,
            caractères génériques LIKE échappés).

    Returns:
        Dict {athlete_name, best_snatch, best_clean_jerk, best_total,
        nb_competitions}. Dict vide si l'athlète est introuvable ou si
        la base est indisponible.
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
        return dict(zip(columns, row))
    except duckdb.Error as exc:
        logger.error("compute_athlete_stats_query_error", error=str(exc))
        return {}
    finally:
        conn.close()


# Registre de dispatch pour le tool_node du graphe (nom d'outil -> fonction).
TOOLS: dict[str, Callable[..., list[dict] | dict]] = {
    "search_regulations": search_regulations,
    "query_results": query_results,
    "compute_athlete_stats": compute_athlete_stats,
}
