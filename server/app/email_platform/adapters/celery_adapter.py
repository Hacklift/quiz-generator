import logging
from ..models import EmailPayload, SendResult
from ..renderer import render_email
from celery.exceptions import CeleryError

logger = logging.getLogger(__name__)

class CeleryAdapter:
    def __init__(self, celery_app):
        self.celery_app = celery_app

    async def send(self, payload: EmailPayload) -> SendResult:
        try:
            ping_result = self.celery_app.control.ping(timeout=1)
            if not ping_result:
                logger.info("No Celery workers available")
                raise RuntimeError("Celery workers down or unavailable")
        except CeleryError as e:
            raise RuntimeError(f"Celery check failed: {e}")

        msg = render_email(payload.template_id, payload.to, payload.template_vars)
        subject = msg["Subject"]
        body = msg.get_payload()
        logger.info(f"[EmailPlatform] Enqueuing Celery task for {payload.to}")
        self.celery_app.send_task(
            "tasks.send_email_generic",
            args=[payload.to, subject, body],
            queue="email",
            ignore_result=True,
        )
        logger.info(f"[EmailPlatform] Enqueued Celery task for {payload.to}")
        return SendResult(ok=True, adapter="celery")
