import os
import ssl
from urllib.parse import urlparse
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("quiz_app", broker=redis_url, backend=redis_url)

parsed = urlparse(redis_url)
env = os.getenv("ENV", "development").lower()

if parsed.scheme == "rediss":
    if env == "production":
        broker_use_ssl = {
            "ssl_cert_reqs": ssl.CERT_REQUIRED,
        }
    else:
        broker_use_ssl = {
            "ssl_cert_reqs": ssl.CERT_NONE, 
        }

    celery_app.conf.broker_use_ssl = broker_use_ssl
    celery_app.conf.redis_backend_use_ssl = broker_use_ssl

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
    broker_connection_retry_on_startup=True,
)

celery_app.conf.task_routes = {
    "tasks.send_quiz_email": {"queue": "email"},
    "tasks.send_email_generic": {"queue": "email"},
}

import server.app.email_platform.email_tasks
