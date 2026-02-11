import pytest

from server.app.email_platform.service import EmailService
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
