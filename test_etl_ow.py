import os
import ssl
import certifi

# 1. On force Python à utiliser les certificats de la librairie certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

# 2. (Optionnel) Si ça ne suffit pas, on désactive la vérification
# ssl._create_default_https_context = ssl._create_unverified_context

import pandas as pd
import duckdb
import requests
from io import StringIO
from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

# Configuration
CSV_URL = "https://raw.githubusercontent.com/euanwm/openweightlifting/development/event_data/IWF/117.csv"
DB_PATH = "data/duckdb/iwf_hub.duckdb"

def test_real_extraction():
    print(f"🚀 Starting extraction test for event 117...")
    
    try:
        # 1. Extraction
        extractor = OpenWeightliftingExtractor(CSV_URL)
        df = extractor.fetch_data()
        print(f"✅ Extracted {len(df)} rows from OpenWeightlifting.")

        # 2. Loading into Raw zone
        loader = DataLoader(DB_PATH)
        loader.load_to_duckdb(df, "ow_event_117")
        print("✅ Data successfully loaded into raw_ow_event_117.")

        # 3. Schema Verification
        conn = duckdb.connect(DB_PATH)
        columns = conn.execute("PRAGMA table_info('raw_ow_event_117')").fetchall()
        col_names = [col[1] for col in columns]
        
        expected_cols = ['lifter_name', 'total', 'date', 'category']
        for col in expected_cols:
            if col in col_names:
                print(f"✅ Column '{col}' verified.")
            else:
                print(f"❌ Column '{col}' missing!")

        conn.execute("DROP TABLE raw_ow_event_117")
        conn.close()
        print("🚀 Test completed successfully.")

    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_real_extraction()
