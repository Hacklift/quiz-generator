import logging
from ..models import EmailPayload, SendResult
from ..renderer import render_email

logger = logging.getLogger(__name__)


class DirectAdapter:
    async def send(self, payload: EmailPayload) -> SendResult:
        from server.app.email_platform.platform_email_utils import send_email

        msg = render_email(payload.template_id, payload.to, payload.template_vars)
        send_email(payload.to, msg)
        logger.info(f"[EmailPlatform] Direct Email sent to {payload.to}")
        return SendResult(ok=True, adapter="direct")
