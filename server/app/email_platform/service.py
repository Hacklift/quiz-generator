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


    async def send_worker_email(
        self,
        *,
        to: str,
        template_id: str,
        template_vars: dict,
        purpose: str,
        priority: str = "default",
    ):
        """Send through adapters that are safe to invoke inside a Celery worker."""
        payload = EmailPayload(to=to, template_id=template_id, template_vars=template_vars)
        return await self.chain.send(payload, worker_chain_for(purpose, priority))


def worker_chain_for(purpose: str, priority: str = "default") -> list[str]:
    """Adapt the platform policy without recursively scheduling another task.

    Celery and FastAPI background adapters are request-dispatch mechanisms, not
    providers. A worker replaces either with direct SMTP while retaining the
    configured Mailgun ordering.
    """
    route: list[str] = []
    for adapter in chain_for(purpose, priority):
        worker_adapter = "direct" if adapter in {"celery", "background", "direct"} else adapter
        if worker_adapter in {"mailgun", "direct"} and worker_adapter not in route:
            route.append(worker_adapter)
    return route


def build_email_service(background: BackgroundTasks | None):
    adapters = {
        "celery": CeleryAdapter(celery_app),
        "direct": DirectAdapter(),
        "mailgun": MailgunAdapter(),
    }
    if background is not None:
        adapters["background"] = BackgroundAdapter(background)
    return EmailService(ChainEmailSender(adapters))


def build_worker_email_service() -> EmailService:
    """Build the non-recursive provider chain used by durable Celery deliveries."""
    return EmailService(
        ChainEmailSender(
            {
                "direct": DirectAdapter(),
                "mailgun": MailgunAdapter(),
            }
        )
    )
