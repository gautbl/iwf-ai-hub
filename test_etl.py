import os
import ssl
import certifi

# 1. On force Python à utiliser les certificats de la librairie certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

# 2. (Optionnel) Si ça ne suffit pas, on désactive la vérification
# ssl._create_default_https_context = ssl._create_unverified_context

from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

# Configuration pour le test
# On utilise un CSV de test public (Données de musculation/fitness)
TEST_URL = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv" 
DB_PATH = "data/duckdb/iwf_hub.duckdb"

def main():
    print("🚀 Lancement du test ETL...")
    
    try:
        # 1. Extraction
        print(f"Tentative d'extraction depuis {TEST_URL}...")
        extractor = OpenWeightliftingExtractor(TEST_URL)
        df = extractor.fetch_data()
        print("✅ Extraction réussie.")

        # 2. Chargement (Load)
        print(f"Chargement dans DuckDB à {DB_PATH}...")
        loader = DataLoader(DB_PATH)
        # On utilise un nom de table de test pour ne pas polluer la table finale
        loader.load_to_duckdb(df, "test_load") 
        print("✅ Chargement réussi.")

        # 3. Vérification
        import duckdb
        conn = duckdb.connect(DB_PATH)
        row_count = conn.execute("SELECT count(*) FROM raw_test_load").fetchone()[0]
        print(f"✅ Vérification faite : {row_count} lignes importées avec succès.")
        
        # Nettoyage après test
        conn.execute("DROP TABLE raw_test_load")
        conn.close()

    except Exception as e:
        print(f"❌ Le test a échoué : {e}")

if __name__ == "__main__":
    main()
