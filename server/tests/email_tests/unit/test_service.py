import pytest

from server.app.email_platform.chain import ChainEmailSender
from server.app.email_platform.service import EmailService, worker_chain_for
from server.app.email_platform.models import SendResult


@pytest.mark.asyncio
async def test_email_service_invokes_chain_and_sender(monkeypatch, email_payload_factory):
    class FakeChain:
        def __init__(self):
            self.called = False
            self.payload = None
            self.route = None

        async def send(self, payload, route):
            self.called = True
            self.payload = payload
            self.route = route
            return SendResult(ok=True, adapter="direct")

    fake_chain = FakeChain()

    monkeypatch.setattr(
        "server.app.email_platform.service.chain_for",
        lambda purpose, priority="default": ["direct"],
        raising=False,
    )

    service = EmailService(fake_chain)
    res = await service.send_email(
        to="a@test.com",
        template_id="verification",
        template_vars={"code": "123"},
        purpose="verification",
    )

    assert fake_chain.called is True
    assert res.ok
    assert fake_chain.route == ["direct"]
    assert fake_chain.payload.to == "a@test.com"
    assert fake_chain.payload.template_id == "verification"


@pytest.mark.asyncio
async def test_worker_email_service_uses_worker_safe_fallback_route(monkeypatch):
    class FakeChain:
        async def send(self, payload, route):
            self.payload = payload
            self.route = route
            return SendResult(ok=True, adapter="direct")

    fake_chain = FakeChain()
    monkeypatch.setattr(
        "server.app.email_platform.service.chain_for",
        lambda purpose, priority="default": ["mailgun", "celery", "background"],
    )

    result = await EmailService(fake_chain).send_worker_email(
        to="a@test.com",
        template_id="custom",
        template_vars={},
        purpose="training_invitation",
    )

    assert result.adapter == "direct"
    assert fake_chain.route == ["mailgun", "direct"]


def test_worker_chain_replaces_dispatch_adapters_with_direct_smtp(monkeypatch):
    monkeypatch.setattr(
        "server.app.email_platform.service.chain_for",
        lambda purpose, priority="default": ["celery", "background", "direct", "mailgun"],
    )

    assert worker_chain_for("verification") == ["direct", "mailgun"]


@pytest.mark.asyncio
async def test_worker_email_service_falls_back_to_direct_smtp(monkeypatch):
    class UnavailableMailgun:
        async def send(self, payload):
            raise RuntimeError("Mailgun unavailable")

    class SuccessfulSmtp:
        async def send(self, payload):
            assert payload.to == "a@test.com"
            return SendResult(ok=True, adapter="direct")

    monkeypatch.setattr(
        "server.app.email_platform.service.chain_for",
        lambda purpose, priority="default": ["mailgun", "celery"],
    )
    service = EmailService(
        ChainEmailSender(
            {
                "mailgun": UnavailableMailgun(),
                "direct": SuccessfulSmtp(),
            }
        )
    )

    result = await service.send_worker_email(
        to="a@test.com",
        template_id="custom",
        template_vars={},
        purpose="training_invitation",
    )

    assert result.adapter == "direct"
