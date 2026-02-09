from fastapi import BackgroundTasks
from .models import EmailPayload
from .policy import chain_for
from .chain import ChainEmailSender
from .adapters.celery_adapter import CeleryAdapter
from .adapters.background_adapter import BackgroundAdapter
from .adapters.direct_adapter import DirectAdapter
from .adapters.mailgun_adapter import MailgunAdapter
from server.celery_config import celery_app

class EmailService:
    def __init__(self, chain: ChainEmailSender):
        self.chain = chain

    async def send_email(self, *, to: str, template_id: str, template_vars: dict, purpose: str, priority: str = "default"):
        payload = EmailPayload(to=to, template_id=template_id, template_vars=template_vars)
        route = chain_for(purpose, priority)
        return await self.chain.send(payload, route)

def build_email_service(background: BackgroundTasks | None):
    adapters = {
        "celery": CeleryAdapter(celery_app),
        "direct": DirectAdapter(),
        "mailgun": MailgunAdapter(),
    }
    if background is not None:
        adapters["background"] = BackgroundAdapter(background)
    return EmailService(ChainEmailSender(adapters))
