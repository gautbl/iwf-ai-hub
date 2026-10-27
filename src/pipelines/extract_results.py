import io
from abc import ABC, abstractmethod

import duckdb
import pandas as pd
import requests
import structlog
from pandas import DataFrame

logger = structlog.get_logger()


class DataExtractor(ABC):
    """Interface for extracting raw data from an external source.

    Concrete subclasses implement fetch_data() to get a DataFrame
    from a URL, an API or a local file.
    """

    @abstractmethod
    def fetch_data(self) -> DataFrame:
        """Fetches data from the source and returns it as a DataFrame.

        Returns:
            DataFrame with the extracted data.

        Raises:
            requests.exceptions.RequestException: HTTP request failed.
        """


class OpenWeightliftingExtractor(DataExtractor):
    """Specialised extractor for OpenWeightlifting data.

    Fetches a CSV file from the openweightlifting GitHub repository
    and loads it into a DataFrame. In production, HTTP headers
    and authentication would be handled by subclassing.
    """

    def __init__(self, url: str):
        """Initialises the extractor with the CSV file URL.

        Args:
            url: complete URL to the CSV file on GitHub.
        """
        self.url = url

    def fetch_data(self) -> DataFrame:
        """Downloads the CSV from the configured URL and returns a DataFrame.

        Returns:
            DataFrame with the CSV file rows.

        Raises:
            requests.exceptions.RequestException: HTTP failure (timeout, 4xx, 5xx).
            pd.errors.EmptyDataError: CSV file empty or invalid.
        """
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))


class DataLoader:
    """Loader of DataFrames into DuckDB (Raw zone).

    Two operation modes:
    - Without event_id: creates or replaces the table (``CREATE OR REPLACE``).
    - With event_id: inserts into a unified table by deleting rows of the
      same event_id before insertion (idempotent).
    """

    def __init__(self, db_path: str):
        """Initialises the loader with the DuckDB database path.

        Args:
            db_path: path to the DuckDB file (created if non-existent).
        """
        self.db_path = db_path

    def load_to_duckdb(
        self, df: DataFrame, table_name: str, event_id: int | None = None
    ) -> None:
        """Loads a DataFrame into a DuckDB table prefixed by ``raw_``.

        Args:
            df: data to insert.
            table_name: logical table name (prefixed by ``raw_`` in DB).
            event_id: event identifier (None = full replacement).
        """
        conn = duckdb.connect(self.db_path)
        if event_id is None:
            conn.execute(
                f"CREATE OR REPLACE TABLE raw_{table_name} AS SELECT * FROM df"
            )
        else:
            df = df.copy()
            df["event_id"] = event_id
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS raw_{table_name} "
                f"AS SELECT * FROM df WHERE 1=0"
            )
            conn.execute(f"DELETE FROM raw_{table_name} WHERE event_id = ?", [event_id])
            conn.execute(f"INSERT INTO raw_{table_name} SELECT * FROM df")
        conn.close()


# Execution example
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