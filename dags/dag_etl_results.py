from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
import os

# Ajout du dossier src au PYTHONPATH pour que Airflow trouve les modules
sys.path.append('/opt/airflow/src')
from pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

def run_etl():
    SOURCE_URL = "https://example.com/results.csv"
    DB_PATH = "/data/duckdb/iwf_hub.duckdb"
    
    extractor = OpenWeightliftingExtractor(SOURCE_URL)
    loader = DataLoader(DB_PATH)
    
    df = extractor.fetch_data()
    loader.load_to_duckdb(df, "results")

with DAG(
    dag_id='iwf_etl_results',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    task_etl = PythonOperator(
        task_id='extract_and_load_results',
        python_callable=run_etl
    )
