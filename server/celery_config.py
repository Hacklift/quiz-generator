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

import os
from urllib.parse import urlparse
import ssl
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL")
celery_app = Celery("quiz_app", broker=redis_url, backend=redis_url)

parsed = urlparse(redis_url)
if parsed.scheme == "rediss":
    celery_app.conf.broker_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE
    }
    celery_app.conf.redis_backend_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE
    }

celery_app.conf.task_routes = {
    "server.tasks.send_quiz_email": {"queue": "email"}
}

import server.app.share.share_tasks
