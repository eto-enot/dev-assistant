import os

import dotenv
from celery import Celery
from celery.signals import worker_process_init
from opentelemetry.instrumentation.celery import CeleryInstrumentor

# uv run celery -A dev_assistant.celery_app worker --concurrency=3 -P solo
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    CeleryInstrumentor().instrument()


celery_app = Celery(
    "dev_assistant",
    broker=REDIS_URL,
    backend="rpc://",
    include=["dev_assistant.celery_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=3,
    result_backend_transport_options={"global_keyprefix": "celery_"},
    worker_hijack_root_logger=False,
)

if __name__ == "__main__":
    dotenv.load_dotenv()
