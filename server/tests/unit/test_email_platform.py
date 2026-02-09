import importlib
import pytest
from fastapi import BackgroundTasks
from email.mime.text import MIMEText

from server.app.email_platform.models import EmailPayload
from server.app.email_platform.adapters.direct_adapter import DirectAdapter
from server.app.email_platform.adapters.celery_adapter import CeleryAdapter
from server.app.email_platform.adapters.background_adapter import BackgroundAdapter


@pytest.mark.asyncio
async def test_direct_adapter_sends_email(monkeypatch):
    sent = {}

    def fake_render(_template_id, _to, _vars):
        msg = MIMEText("body")
        msg["Subject"] = "subject"
        msg["To"] = _to
        return msg

    def fake_send_email(to, msg):
        sent["to"] = to
        sent["subject"] = msg["Subject"]

    monkeypatch.setattr("server.app.email_platform.adapters.direct_adapter.render_email", fake_render)
    monkeypatch.setattr("server.app.email_platform.adapters.direct_adapter.send_email", fake_send_email)

    adapter = DirectAdapter()
    payload = EmailPayload(to="user@example.com", template_id="custom", template_vars={})

    result = await adapter.send(payload)
    assert result.ok is True
    assert sent["to"] == "user@example.com"


@pytest.mark.asyncio
async def test_celery_adapter_enqueues_task(monkeypatch):
    class FakeControl:
        def ping(self, timeout=1):
            return ["pong"]

    class FakeCelery:
        def __init__(self):
            self.control = FakeControl()
            self.sent = None

        def send_task(self, name, args=None, queue=None, ignore_result=None):
            self.sent = {"name": name, "args": args, "queue": queue}

    def fake_render(_template_id, _to, _vars):
        msg = MIMEText("body")
        msg["Subject"] = "subject"
        return msg

    monkeypatch.setattr("server.app.email_platform.adapters.celery_adapter.render_email", fake_render)

    celery_app = FakeCelery()
    adapter = CeleryAdapter(celery_app)
    payload = EmailPayload(to="user@example.com", template_id="custom", template_vars={})

    result = await adapter.send(payload)
    assert result.ok is True
    assert celery_app.sent["name"] == "tasks.send_email_generic"


@pytest.mark.asyncio
async def test_background_adapter_uses_background_tasks(monkeypatch):
    def fake_render(_template_id, _to, _vars):
        msg = MIMEText("body")
        msg["Subject"] = "subject"
        return msg

    monkeypatch.setattr("server.app.email_platform.adapters.background_adapter.render_email", fake_render)

    background = BackgroundTasks()
    adapter = BackgroundAdapter(background)
    payload = EmailPayload(to="user@example.com", template_id="custom", template_vars={})

    result = await adapter.send(payload)
    assert result.ok is True
    assert len(background.tasks) == 1


def test_policy_selects_correct_chain(monkeypatch):
    monkeypatch.setenv("PRIMARY_EMAIL_PROVIDER", "mailgun")
    policy = importlib.reload(importlib.import_module("server.app.email_platform.policy"))
    assert policy.chain_for("verification")[:1] == ["mailgun"]

    monkeypatch.setenv("PRIMARY_EMAIL_PROVIDER", "smtp")
    policy = importlib.reload(importlib.import_module("server.app.email_platform.policy"))
    assert policy.chain_for("verification")[0] == "celery"


def test_renderer_builds_verification_and_reset(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com")
    renderer = importlib.reload(importlib.import_module("server.app.email_platform.renderer"))

    verify = renderer.render_email(
        "verification",
        "user@example.com",
        {"code": "123456", "token": "abc"},
    )
    assert "verify-email" in verify.get_payload()

    reset = renderer.render_email(
        "password_reset",
        "user@example.com",
        {"code": "123456", "token": "xyz"},
    )
    assert "reset-password" in reset.get_payload()
