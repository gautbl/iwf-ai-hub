import os
import ssl
import certifi
import pytest
import duckdb
from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

# Fix SSL certificates for the environment
os.environ['SSL_CERT_FILE'] = certifi.where()

# Configuration
TEST_URL = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv" 
DB_PATH = "data/duckdb/test_iwf_hub.duckdb" # Use a separate test DB

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """Sets up the test database before tests and cleans up after."""
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    yield # This is where the tests run
    
    # Cleanup: Delete the test database after all tests in the module finish
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_extraction():
    """Tests if the extractor can fetch data from the URL."""
    print("\nTesting extraction...")
    extractor = OpenWeightliftingExtractor(TEST_URL)
    df = extractor.fetch_data()
    assert df is not None
    assert not df.empty
    print("✅ Extraction successful.")

def test_loading_to_duckdb():
    """Tests if the DataLoader correctly inserts data into DuckDB."""
    print("\nTesting loading...")
    # We need data to load; reuse extractor or create a sample DataFrame
    from pandas import DataFrame
    sample_df = DataFrame({"PassengerId": [1, 2], "Survived": [0, 1]})
    
    loader = DataLoader(DB_PATH)
    loader.load_to_duckdb(sample_df, "test_load")
    
    # Verify the data exists in the DB
    conn = duckdb.connect(DB_PATH)
    count = conn.execute("SELECT count(*) FROM raw_test_load").fetchone()[0]
    conn.close()
    
    assert count == 2
    print("✅ Loading successful.")

def test_etl_full_pipeline():
    """Integration test for the full ETL flow."""
    print("\nTesting full ETL flow...")
    extractor = OpenWeightliftingExtractor(TEST_URL)
    df = extractor.fetch_data()
    
    loader = DataLoader(DB_PATH)
    loader.load_to_duckdb(df, "test_full_flow")
    
    conn = duckdb.connect(DB_PATH)
    count = conn.execute("SELECT count(*) FROM raw_test_full_flow").fetchone()[0]
    conn.close()
    
    assert count > 0
    print("✅ Full ETL flow successful.")