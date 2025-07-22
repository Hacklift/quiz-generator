from celery import Celery
import logging

logger = logging.getLogger(__name__)

celery = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["server.tasks"]
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"]
)

logger.info("Celery configured and ready to go.")

