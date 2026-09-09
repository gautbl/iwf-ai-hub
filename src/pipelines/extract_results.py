import io
import requests
import duckdb
import structlog
import pandas as pd
from abc import ABC, abstractmethod

from pandas import DataFrame

logger = structlog.get_logger()


class DataExtractor(ABC):
    @abstractmethod
    def fetch_data(self) -> DataFrame:
        pass


class OpenWeightliftingExtractor(DataExtractor):
    def __init__(self, url: str):
        self.url = url

    def fetch_data(self) -> DataFrame:
        # Simulation d'extraction : On récupère un CSV ou JSON depuis l'URL
        # Dans un cas réel, on gérerait les headers et l'authentification
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))


class DataLoader:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def load_to_duckdb(self, df: DataFrame, table_name: str) -> None:
        conn = duckdb.connect(self.db_path)
        # Injection dans la zone 'Raw' — CREATE OR REPLACE rend la tâche idempotente
        conn.execute(f"CREATE OR REPLACE TABLE raw_{table_name} AS SELECT * FROM df")
        conn.close()


# Exemple d'exécution
if __name__ == "__main__":
    # URL de test ou source IWF réelle
    SOURCE_URL = "https://example.com/results.csv"
    DB_PATH = "data/duckdb/iwf_hub.duckdb"

    extractor = OpenWeightliftingExtractor(SOURCE_URL)
    loader = DataLoader(DB_PATH)

    try:
        df_results = extractor.fetch_data()
        loader.load_to_duckdb(df_results, "results")
        logger.info("raw_loaded", table="resources")
    except Exception as e:
        logger.error("load_failed", error=str(e))
