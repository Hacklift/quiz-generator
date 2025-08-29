from ..models import EmailPayload, SendResult
from ..renderer import render_email
from server.app.share.share_email_utils import send_email

class DirectAdapter:
    async def send(self, payload: EmailPayload) -> SendResult:
        msg = render_email(payload.template_id, payload.to, payload.template_vars)
        # synchronous (blocking) last-resort send
        send_email(payload.to, msg)
        return SendResult(ok=True, adapter="direct")
