import base64
import fnmatch
import logging
import os
import warnings

import gitlab
from airflow.models import DAG, Variable
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from dev_assistant.chunking import SourceCodeNodeParser
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient

warnings.filterwarnings("ignore")
logging.basicConfig(filename="gitlab_indexer.log", level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler())

DAG_ID = "gitlab_indexer"
logger = logging.getLogger("dev-assistant.indexer")

GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")
GITLAB_URL = os.environ.get("GITLAB_URL")
QDRANT_URL = os.environ.get("QDRANT_URL")
API_BASE_URL = os.environ.get("API_BASE_URL")
RAG_COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "code")
RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", 256))
GITLAB_FILE_FILTER = os.environ.get("GITLAB_FILE_FILTER", "*.*")
GITLAB_FILE_FILTERS = GITLAB_FILE_FILTER.split(";")


def get_main_branch(project):
    branches = set(branch.name for branch in project.branches.list(get_all=True))
    if "master" in branches:
        return "master"
    elif "main" in branches:
        return "main"
    else:
        return None


def get_project_files(project, branch):
    stack = [""]
    while stack:
        path = stack.pop()
        items = project.repository_tree(path=path, ref=branch, get_all=True)
        for item in items:
            if item["type"] == "tree":
                stack.append(item["path"])
            elif item["type"] == "blob":
                yield item["path"]


def get_file_content(project, branch, path):
    file = project.files.get(path, ref=branch)
    return base64.b64decode(file.content).decode("utf-8")


def create_index():
    aclient = AsyncQdrantClient(url=QDRANT_URL)
    client = QdrantClient(url=QDRANT_URL)

    if client.collection_exists(RAG_COLLECTION_NAME):
        client.delete_collection(RAG_COLLECTION_NAME)

    vector_store = QdrantVectorStore(
        client=client,
        aclient=aclient,
        collection_name=RAG_COLLECTION_NAME,
        enable_hybrid=True,
        fastembed_sparse_model="Qdrant/bm25",
    )

    context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex([], storage_context=context, store_nodes_override=True)

    return index


def is_match(path):
    is_match = False
    for filter in GITLAB_FILE_FILTERS:
        if fnmatch.fnmatch(path, filter):
            is_match = True
            break
    return is_match


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
    if not GITLAB_TOKEN:
        raise KeyError("Gitlab access token is not set.")

    if not GITLAB_URL:
        raise KeyError("Gitlab base url is not set.")

    if not QDRANT_URL:
        raise KeyError("Qdrant url is not set.")

    logger.info("GITLAB_URL: %s", GITLAB_URL)
    logger.info("QDRANT_URL: %s", QDRANT_URL)
    logger.info("API_BASE_URL: %s", API_BASE_URL)
    logger.info("RAG_COLLECTION_NAME: %s", RAG_COLLECTION_NAME)
    logger.info("RAG_CHUNK_SIZE: %s", RAG_CHUNK_SIZE)
    logger.info("GITLAB_FILE_FILTER: %s", GITLAB_FILE_FILTER)

    logger.info("Starting processing GitLab repos.")

    Settings.llm = None
    Settings.embed_model = None
    if API_BASE_URL:
        Settings.embed_model = OpenAILikeEmbedding(
            model_name="Embedding Model", api_base=API_BASE_URL
        )

    index = create_index()
    parser = SourceCodeNodeParser(chunk_size=RAG_CHUNK_SIZE)
    cnt = 1

    with gitlab.Gitlab(
        url=GITLAB_URL, private_token=GITLAB_TOKEN, ssl_verify=False, keep_base_url=True
    ) as gl:
        gl.auth()
        for project in gl.projects.list(iterator=True):
            logger.info("Processing repo %s", project.name_with_namespace)
            logger.info("Reading files")

            docs = []
            branch = get_main_branch(project)
            for path in filter(is_match, get_project_files(project, branch)):
                file = project.files.get(path, ref=branch)
                content = base64.b64decode(file.content).decode("utf-8")
                metadata = {
                    "file_path": path,
                    "file_name": file.file_name,
                    "file_size": file.size,
                }
                doc = Document(text=content, metadata=metadata)
                docs.append(doc)

            logger.info("Parsing files")
            nodes = parser(docs)

            logger.info("Generating embeddings")
            index.insert_nodes(nodes)

            logger.info("Done processing repo %s", project.name_with_namespace)

            cnt += 1

    logger.info("Done processing GitLab repos.")


index_gitlab_repos = PythonOperator(
    task_id="index_gitlab_repos", python_callable=index_gitlab_repos, dag=dag
)


index_gitlab_repos
