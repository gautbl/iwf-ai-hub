import requests
import duckdb
import pandas as pd
from abc import ABC, abstractmethod

class DataExtractor(ABC):
    @abstractmethod
    def fetch_data(self):
        pass

class OpenWeightliftingExtractor(DataExtractor):
    def __init__(self, url):
        self.url = url

    def fetch_data(self):
        # Simulation d'extraction : On récupère un CSV ou JSON depuis l'URL
        # Dans un cas réel, on gérerait les headers et l'authentification
        response = requests.get(self.url)
        if response.status_code == 200:
            return pd.read_csv(self.url) # Hypothèse que la source est un CSV
        else:
            raise Exception(f"Failed to fetch data from {self.url}")

class DataLoader:
    def __init__(self, db_path):
        self.db_path = db_path

    def load_to_duckdb(self, df, table_name):
        conn = duckdb.connect(self.db_path)
        # Injection dans la zone 'Raw'
        conn.execute(f"CREATE TABLE IF NOT EXISTS raw_{table_name} AS SELECT * FROM df")
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
        print("Données injectées avec succès dans la zone Raw.")
    except Exception as e:
        print(f"Erreur : {e}")
