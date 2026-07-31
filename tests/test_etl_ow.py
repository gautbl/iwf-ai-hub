import os
import ssl
import certifi
import pytest
import pandas as pd
import duckdb
from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

# Fix SSL certificates for the environment
os.environ['SSL_CERT_FILE'] = certifi.where()

# Configuration
CSV_URL = "https://raw.githubusercontent.com/euanwm/openweightlifting/development/event_data/IWF/117.csv"
DB_PATH = "data/duckdb/iwf_hub.duckdb"

@pytest.fixture(scope="module", autouse=True)
def manage_test_db():
    """
    Fixture to ensure the database path exists and clean up 
    the specific test table after the test suite runs.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    yield
    # Cleanup: remove the temporary table created during testing
    conn = duckdb.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS raw_ow_event_117")
    conn.execute("DROP TABLE IF EXISTS raw_results")
    conn.execute("DROP TABLE IF EXISTS dim_athletes")
    conn.execute("DROP TABLE IF EXISTS dim_weight_classes")
    conn.execute("DROP TABLE IF EXISTS fct_results")
    conn.execute("DROP VIEW IF EXISTS stg_results")
    conn.close()

def test_ow_extraction_and_loading():
    """
    Tests the full pipeline: extracting real IWF data from the CSV 
    repository and loading it into the DuckDB raw zone.
    """
    # 1. Extraction
    extractor = OpenWeightliftingExtractor(CSV_URL)
    df = extractor.fetch_data()
    
    assert df is not None, "Extractor failed to return a DataFrame"
    assert not df.empty, "Extracted DataFrame is empty"
    
    # 2. Loading into DuckDB
    loader = DataLoader(DB_PATH)
    loader.load_to_duckdb(df, "ow_event_117")
    
    # 3. Database Verification
    conn = duckdb.connect(DB_PATH)
    
    # Verify table existence
    table_exists = conn.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'raw_ow_event_117'"
    ).fetchone()[0]
    assert table_exists == 1, "Table raw_ow_event_117 was not created in DuckDB"
    
    # Verify specific columns based on scraped content
    # Expected columns from the provided CSV content: event, date, category, lifter_name, etc.
    columns = [col[1] for col in conn.execute("PRAGMA table_info('raw_ow_event_117')").fetchall()]
    
    expected_cols = ['lifter_name', 'total', 'date', 'category']
    for col in expected_cols:
        assert col in columns, f"Column '{col}' missing from raw_ow_event_117"
    
    # Verify data content (checking if the first lifter from the CSV is present)
    first_lifter = conn.execute("SELECT lifter_name FROM raw_ow_event_117 LIMIT 1").fetchone()[0]
    assert first_lifter == "BARU Morea", f"Data mismatch: expected BARU Morea, got {first_lifter}"
    
    conn.close()

def test_full_etl_pipeline():
    """
    End-to-End Test: From CSV Extraction to Star Schema population.
    """
    # 1. EXTRACTION PHASE
    # Validate that we can fetch real data from the source
    extractor = OpenWeightliftingExtractor(CSV_URL)
    df = extractor.fetch_data()
    
    assert df is not None, "Extractor failed to return a DataFrame"
    assert not df.empty, "The extracted DataFrame is empty"
    # Based on the scraped content, we expect 'lifter_name' to be present
    assert 'lifter_name' in df.columns, "CSV columns do not match expected schema"

    # 2. RAW LOADING PHASE
    # Load the scraped data into the DuckDB raw zone
    loader = DataLoader(DB_PATH)
    loader.load_to_duckdb(df, "ow_event_117")
    
    conn = duckdb.connect(DB_PATH)
    
    # Verify data exists in the raw table
    raw_count = conn.execute("SELECT count(*) FROM raw_ow_event_117").fetchone()[0]
    assert raw_count > 0, "Raw table 'raw_ow_event_117' is empty"
    
    # 3. TRANSFORMATION PHASE (Simulating dbt logic)
    # In your production environment, you would call `dbt run` via shell.
    # Here we implement the logic directly to verify SQL correctness.
    
    # Staging: Cleaning and casting
    conn.execute("""
        CREATE OR REPLACE VIEW stg_results AS 
        SELECT 
            TRIM(lifter_name) as athlete_name, 
            CAST(date AS DATE) as event_date, 
            TRIM(category) as category_name, 
            CAST(best_snatch AS DOUBLE) as snatch_total, 
            CAST(best_cj AS DOUBLE) as clean_jerk_total, 
            CAST(total AS DOUBLE) as combined_total 
        FROM raw_ow_event_117
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
    raw_count_final = conn.execute("SELECT count(*) FROM raw_ow_event_117").fetchone()[0]
    fact_count = conn.execute("SELECT count(*) FROM fct_results").fetchone()[0]
    
    assert raw_count_final == fact_count, f"Data loss detected! Raw: {raw_count_final}, Fact: {fact_count}"
    
    # Verify a specific record from the CSV sample (e.g., BARU Morea)
    # This ensures that not only the count is correct, but the JOIN logic worked
    record = conn.execute("""
        SELECT a.name 
        FROM fct_results f 
        JOIN dim_athletes a ON f.athlete_id = a.athlete_id 
        WHERE a.name = 'BARU Morea' LIMIT 1
    """).fetchone()
    
    assert record is not None, "The data for 'BARU Morea' did not propagate to the Star Schema"
    assert record[0] == "BARU Morea"

    conn.close()