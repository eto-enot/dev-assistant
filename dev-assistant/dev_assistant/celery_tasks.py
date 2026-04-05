import os
import logging

try:
    from dev_assistant.celery_app import celery_app
    from dev_assistant.otel_logging import setup_otel_logging
except ImportError:    
    from celery_app import celery_app
    from otel_logging import setup_otel_logging


setup_otel_logging()
logger = logging.getLogger('dev-assistant.tasks')
logger.info(logger.handlers)
logger.info(os.environ.get('OTEL_SERVICE_NAME'))

@celery_app.task(bind=True, name='reindex_project')
def reindex_project_task(self, work_directory: str):
    logger.info('Starting project indexing')
    logger.info('Done project indexing')