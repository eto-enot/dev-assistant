import logging

import dotenv

try:
    from dev_assistant.celery_app import celery_app
except ImportError:
    from celery_app import celery_app


@celery_app.task(bind=True, name="reindex_project")
def reindex_project_task(self, work_directory: str):
    from dev_assistant.config import DevAssistantConfig
    from dev_assistant.otel_logging import setup_otel_logging
    from dev_assistant.rag import DevAssistantRag

    dotenv.load_dotenv()
    setup_otel_logging()
    logger = logging.getLogger("dev-assistant.tasks")
    logger.setLevel(logging.INFO)

    logger.info("Starting project indexing")
    config = DevAssistantConfig.from_env()
    rag = DevAssistantRag(config)
    rag.create_index(work_directory)
    logger.info("Done project indexing")
