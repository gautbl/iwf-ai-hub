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

    def load_to_duckdb(
        self, df: DataFrame, table_name: str, event_id: int | None = None
    ) -> None:
        conn = duckdb.connect(self.db_path)
        if event_id is None:
            # Injection dans la zone 'Raw' — CREATE OR REPLACE rend la tâche idempotente
            conn.execute(f"CREATE OR REPLACE TABLE raw_{table_name} AS SELECT * FROM df")
        else:
            # Table unifiée : on empile les events, idempotent par event_id
            df = df.copy()
            df["event_id"] = event_id
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS raw_{table_name} AS SELECT * FROM df WHERE 1=0"
            )
            conn.execute(f"DELETE FROM raw_{table_name} WHERE event_id = ?", [event_id])
            conn.execute(f"INSERT INTO raw_{table_name} SELECT * FROM df")
        conn.close()


# Exemple d'exécution
if __name__ == "__main__":
    BASE_URL = (
        "https://raw.githubusercontent.com/euanwm/openweightlifting/"
        "development/event_data/IWF"
    )
    EVENT_IDS = [117, 119, 120]
    DB_PATH = "data/duckdb/iwf_hub.duckdb"

    loader = DataLoader(DB_PATH)

    for event_id in EVENT_IDS:
        try:
            extractor = OpenWeightliftingExtractor(f"{BASE_URL}/{event_id}.csv")
            df_results = extractor.fetch_data()
            loader.load_to_duckdb(df_results, "ow_events", event_id=event_id)
            logger.info("raw_loaded", event_id=event_id, rows=len(df_results))
        except Exception as e:
            logger.error("load_failed", event_id=event_id, error=str(e))
