import io
import requests
import duckdb
import structlog
import pandas as pd
from abc import ABC, abstractmethod

from pandas import DataFrame

logger = structlog.get_logger()


class DataExtractor(ABC):
    """Interface d'extraction de données brutes depuis une source externe.

    Les sous-classes concrètes implémentent fetch_data() pour récupérer
    un DataFrame depuis une URL, une API ou un fichier local.
    """

    @abstractmethod
    def fetch_data(self) -> DataFrame:
        """Récupère les données depuis la source et les retourne sous forme de DataFrame.

        Returns:
            DataFrame contenant les données extraites.

        Raises:
            requests.exceptions.RequestException: échec de la requête HTTP.
        """


class OpenWeightliftingExtractor(DataExtractor):
    """Extracteur spécialisé pour les données OpenWeightlifting.

    Récupère un fichier CSV depuis le dépôt GitHub openweightlifting
    et le charge dans un DataFrame. En production, les headers HTTP
    et l'authentification seraient gérés par le sous-classement.
    """

    def __init__(self, url: str):
        """Initialise l'extracteur avec l'URL du fichier CSV.

        Args:
            url: URL complète vers le fichier CSV sur GitHub.
        """
        self.url = url

    def fetch_data(self) -> DataFrame:
        """Télécharge le CSV depuis l'URL configurée et le retourne en DataFrame.

        Returns:
            DataFrame contenant les lignes du fichier CSV.

        Raises:
            requests.exceptions.RequestException: échec HTTP (timeout, 4xx, 5xx).
            pd.errors.EmptyDataError: fichier CSV vide ou invalide.
        """
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))


class DataLoader:
    """Chargeur de DataFrames dans DuckDB (zone Raw).

    Deux modes de fonctionnement :
    - Sans event_id : crée ou remplace la table (``CREATE OR REPLACE``).
    - Avec event_id : insère dans une table unifiée en supprimant
      les lignes du même event_id avant insertion (idempotent).
    """

    def __init__(self, db_path: str):
        """Initialise le chargeur avec le chemin de la base DuckDB.

        Args:
            db_path: chemin vers le fichier DuckDB (créé si inexistant).
        """
        self.db_path = db_path

    def load_to_duckdb(
        self, df: DataFrame, table_name: str, event_id: int | None = None
    ) -> None:
        """Charge un DataFrame dans une table DuckDB préfixée par ``raw_``.

        Args:
            df: données à insérer.
            table_name: nom logique de la table (préfixé par ``raw_`` en base).
            event_id: identifiant d'événement (None = remplacement total).
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
            conn.execute(
                f"DELETE FROM raw_{table_name} WHERE event_id = ?", [event_id]
            )
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
