import logging
from fastapi import BackgroundTasks
from ..models import EmailPayload, SendResult
from ..renderer import render_email

logger = logging.getLogger(__name__)

class BackgroundAdapter:
    def __init__(self, background: BackgroundTasks):
        self.background = background

    async def send(self, payload: EmailPayload) -> SendResult:
        from server.app.email_platform.platform_email_utils import send_email, sender_email

        msg = render_email(
            payload.template_id,
            payload.to,
            payload.template_vars,
            sender_email=sender_email,
        )
        logger.info(f"[EmailPlatform] Scheduling BackgroundTasks send for {payload.to}")
        self.background.add_task(send_email, payload.to, msg)
        return SendResult(ok=True, adapter="background")
