import os
import certifi
import pytest
import duckdb
from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

# Fix SSL certificates for the environment
os.environ['SSL_CERT_FILE'] = certifi.where()

# Configuration
BASE_URL = "https://raw.githubusercontent.com/euanwm/openweightlifting/development/event_data/IWF"
EVENT_IDS = [117, 119, 120]
DB_PATH = "data/duckdb/test_iwf_hub.duckdb"
RAW_TABLE = "ow_events"

pytestmark = pytest.mark.network

@pytest.fixture(scope="module", autouse=True)
def manage_test_db():
    """
    Fixture to ensure the database path exists and clean up
    the generated tables after the test suite runs.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    yield
    # Cleanup: remove the tables/views created during testing
    conn = duckdb.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS raw_ow_events")
    conn.execute("DROP VIEW IF EXISTS stg_results")
    conn.execute("DROP TABLE IF EXISTS dim_athletes")
    conn.execute("DROP TABLE IF EXISTS dim_weight_classes")
    conn.execute("DROP TABLE IF EXISTS fct_results")
    conn.close()

@pytest.mark.parametrize("event_id", EVENT_IDS)
def test_ow_extraction_and_loading(event_id):
    """
    Tests the pipeline for a given event: extracting real IWF data from the
    CSV repository and loading it into the unified DuckDB raw zone.
    """
    # 1. Extraction
    extractor = OpenWeightliftingExtractor(f"{BASE_URL}/{event_id}.csv")
    df = extractor.fetch_data()

    assert df is not None, "Extractor failed to return a DataFrame"
    assert not df.empty, "Extracted DataFrame is empty"

    # 2. Loading into DuckDB (unified table)
    loader = DataLoader(DB_PATH)
    loader.load_to_duckdb(df, RAW_TABLE, event_id=event_id)

    # 3. Database Verification
    conn = duckdb.connect(DB_PATH)

    count = conn.execute(
        "SELECT count(*) FROM raw_ow_events WHERE event_id = ?", [event_id]
    ).fetchone()[0]
    assert count > 0, f"No rows found in raw_ow_events for event {event_id}"

    # Verify specific columns based on scraped content
    columns = [col[1] for col in conn.execute("PRAGMA table_info('raw_ow_events')").fetchall()]
    expected_cols = ['lifter_name', 'total', 'date', 'category', 'event_id']
    for col in expected_cols:
        assert col in columns, f"Column '{col}' missing from raw_ow_events"

    conn.close()

def test_full_etl_pipeline():
    """
    End-to-End Test: From CSV Extraction to Star Schema population.
    """
    # 1. EXTRACTION PHASE + 2. RAW LOADING PHASE
    loader = DataLoader(DB_PATH)
    for event_id in EVENT_IDS:
        extractor = OpenWeightliftingExtractor(f"{BASE_URL}/{event_id}.csv")
        df = extractor.fetch_data()

        assert df is not None, "Extractor failed to return a DataFrame"
        assert not df.empty, "The extracted DataFrame is empty"
        assert 'lifter_name' in df.columns, "CSV columns do not match expected schema"

        loader.load_to_duckdb(df, RAW_TABLE, event_id=event_id)

    conn = duckdb.connect(DB_PATH)

    # Verify data exists in the unified raw table
    raw_count = conn.execute("SELECT count(*) FROM raw_ow_events").fetchone()[0]
    assert raw_count > 0, "Raw table 'raw_ow_events' is empty"

    # 3. TRANSFORMATION PHASE (Simulating dbt logic)
    # In your production environment, you would call `dbt run` via shell.
    # Here we implement the logic directly to verify SQL correctness.

    # Staging: Cleaning and casting
    conn.execute("""
        CREATE OR REPLACE VIEW stg_results AS 
        SELECT 
            event_id,
            event as event_name,
            TRIM(lifter_name) as athlete_name, 
            CAST(date AS DATE) as event_date, 
            TRIM(category) as category_name, 
            CAST(best_snatch AS DOUBLE) as snatch_total, 
            CAST(best_cj AS DOUBLE) as clean_jerk_total, 
            CAST(total AS DOUBLE) as combined_total 
        FROM raw_ow_events
    """)

    # Dimensional Modeling: Create Dim Tables
    conn.execute("""
        CREATE OR REPLACE TABLE dim_athletes AS 
        SELECT row_number() OVER () as athlete_id, athlete_name as name, 'Unknown' as country 
        FROM stg_results GROUP BY athlete_name
    """)

    conn.execute("""
        CREATE OR REPLACE TABLE dim_weight_classes AS 
        SELECT row_number() OVER () as class_id, category_name 
        FROM stg_results GROUP BY category_name
    """)

    # Fact Table: Join facts with dimensions
    conn.execute("""
        CREATE OR REPLACE TABLE fct_results AS 
        SELECT 
            row_number() OVER () as result_id, 
            a.athlete_id, 
            s.event_date, 
            wc.class_id, 
            s.snatch_total, 
            s.clean_jerk_total, 
            s.combined_total 
        FROM stg_results s 
        JOIN dim_athletes a ON s.athlete_name = a.name 
        JOIN dim_weight_classes wc ON s.category_name = wc.category_name
    """)

    # 4. FINAL INTEGRITY VERIFICATION
    # Ensure every record in raw made it into the fact table
    raw_count_final = conn.execute("SELECT count(*) FROM raw_ow_events").fetchone()[0]
    fact_count = conn.execute("SELECT count(*) FROM fct_results").fetchone()[0]

    assert raw_count_final == fact_count, f"Data loss detected! Raw: {raw_count_final}, Fact: {fact_count}"

    # Verify a real lifter from the raw zone propagates to the Star Schema
    # This ensures that not only the count is correct, but the JOIN logic worked
    lifter_name = conn.execute("SELECT lifter_name FROM raw_ow_events WHERE lifter_name IS NOT NULL LIMIT 1").fetchone()[0]
    record = conn.execute("""
        SELECT a.name 
        FROM fct_results f 
        JOIN dim_athletes a ON f.athlete_id = a.athlete_id 
        WHERE a.name = ? LIMIT 1
    """, (lifter_name,)).fetchone()

    assert record is not None, f"The data for {lifter_name!r} did not propagate to the Star Schema"
    assert record[0] == lifter_name

    conn.close()
