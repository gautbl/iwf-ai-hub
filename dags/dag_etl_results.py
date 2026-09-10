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

# Liste configurable des events IWF à ingérer
BASE_URL = (
    "https://raw.githubusercontent.com/euanwm/openweightlifting/"
    "development/event_data/IWF"
)
EVENT_IDS = [117, 119, 120]

def on_failure_callback(context):
    task_id = context.get("task_instance", {}).task_id if context.get("task_instance") else "unknown"
    logger.error("task_failed", dag="iwf_performance_pipeline", task_id=task_id)

def run_extraction():
    # Chemin absolu dans le conteneur Docker
    DB_PATH = "/data/duckdb/iwf_hub.duckdb"

    # Créer le répertoire si nécessaire
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    loader = DataLoader(DB_PATH)
    failures = []

    for event_id in EVENT_IDS:
        try:
            extractor = OpenWeightliftingExtractor(f"{BASE_URL}/{event_id}.csv")
            df = extractor.fetch_data()
            loader.load_to_duckdb(df, "ow_events", event_id=event_id)
            logger.info("extraction_success", event_id=event_id, rows=len(df))
        except Exception as e:
            logger.error("extraction_failed", event_id=event_id, error=str(e))
            failures.append(event_id)

    if failures:
        raise RuntimeError(f"Extraction failed for events: {failures}")

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
