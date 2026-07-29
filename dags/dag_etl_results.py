from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
import sys

# Import your extraction script
# Assume the extract_results.py is available in the python path
from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

def run_extraction():
    SOURCE_URL = "https://example.com/117.csv" # Actual IWF source
    DB_PATH = "data/duckdb/iwf_hub.duckdb"
    
    extractor = OpenWeightliftingExtractor(SOURCE_URL)
    loader = DataLoader(DB_PATH)
    
    df = extractor.fetch_data()
    loader.load_to_duckdb(df, "ow_event_117")
    print("Extraction complete.")

with DAG(
    dag_id='iwf_performance_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@weekly', 
    catchup=False
) as dag:

    extract_task = PythonOperator(
        task_id='extract_results',
        python_callable=run_extraction
    )

    # This assumes dbt-duckdb is installed in the Airflow environment
    # It runs all models in the current dbt project
    dbt_transform_task = BashOperator(
        task_id='dbt_transform',
        bash_command='dbt run --profiles-dir . --project-dir dbt'
    )
    
    # Step 3: Data Quality Testing
    test_task = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt && dbt test' 
        # Note: Using 'cd' ensures it runs in the correct project directory
)

    extract_task >> dbt_transform_task >> test_task
