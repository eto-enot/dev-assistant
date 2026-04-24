import base64
import logging
import os

import gitlab
from airflow.models import DAG, Variable
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from dev_assistant.chunking import SourceCodeNodeParser


logging.basicConfig(filename="gitlab_indexer.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())

DAG_ID = "gitlab_indexer"
logger = logging.getLogger("dev-assistant.indexer")


args = {
    "owner": "Some User",
    "email": ["aaa@bbb"],
}

dag = DAG(
    dag_id=DAG_ID,
    default_args=args,
    max_active_runs=1,
    concurrency=3,
    schedule_interval="0 0 * * *",
    start_date=days_ago(1),
    tags=["gitlab", "rag", "indexing"],
)


def index_gitlab_repos() -> None:
    logger.info(os.getcwd())
    logger.info(os.getuid())


index_gitlab_repos = PythonOperator(
    task_id="index_gitlab_repos", python_callable=index_gitlab_repos, dag=dag
)


index_gitlab_repos
