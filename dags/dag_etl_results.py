from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import structlog
import sys
import os

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, '/opt/airflow')

from src.pipelines.extract_results import OpenWeightliftingExtractor, DataLoader

logger = structlog.get_logger()

def on_failure_callback(context):
    task_id = context.get("task_instance", {}).task_id if context.get("task_instance") else "unknown"
    logger.error("task_failed", dag="iwf_performance_pipeline", task_id=task_id)

def run_extraction():
    # URL réelle OpenWeightlifting (exemple avec l'event 117)
    SOURCE_URL = "https://raw.githubusercontent.com/euanwm/openweightlifting/development/event_data/IWF/117.csv"
    # Chemin absolu dans le conteneur Docker
    DB_PATH = "/data/duckdb/iwf_hub.duckdb"
    
    # Créer le répertoire si nécessaire
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    try:
        extractor = OpenWeightliftingExtractor(SOURCE_URL)
        loader = DataLoader(DB_PATH)
        
        df = extractor.fetch_data()
        loader.load_to_duckdb(df, "ow_event_117")
        logger.info("extraction_success", rows=len(df))
    except Exception as e:
        logger.error("extraction_failed", error=str(e))
        raise

DEFAULT_ARGS = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": on_failure_callback,
}

with DAG(
    dag_id='iwf_performance_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@weekly', 
    catchup=False,
    tags=['iwf', 'etl', 'performance'],
    default_args=DEFAULT_ARGS
) as dag:

    extract_task = PythonOperator(
        task_id='extract_results',
        python_callable=run_extraction
    )

    # This assumes dbt-duckdb is installed in the Airflow environment
    # It runs all models in the current dbt project
    dbt_transform_task = BashOperator(
        task_id='dbt_transform',
        bash_command='dbt run',
        cwd='/opt/airflow/dbt',  # Répertoire de travail explicite
        env={'DBT_PROFILES_DIR': '/opt/airflow/dbt'}
    )
    
    # Step 3: Data Quality Testing
    dbt_test_task = BashOperator(
        task_id='dbt_test',
        bash_command='dbt test',
        cwd='/opt/airflow/dbt',
        env={'DBT_PROFILES_DIR': '/opt/airflow/dbt'}
)

    extract_task >> dbt_transform_task >> dbt_test_task
