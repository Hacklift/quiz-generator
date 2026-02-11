import pytest

from server.app.email_platform import email_tasks
from server.app.email_platform.platform_email_utils import sender_email


def test_send_email_generic_calls_platform_send(monkeypatch):
    calls = []

    def fake_send(recipient, message):
        calls.append((recipient, message))

    monkeypatch.setattr("server.app.email_platform.email_tasks.send_email", fake_send)

    recipient = "int-recipient@example.com"
    subject = "integration-subject"
    body = "the body"

    orig = getattr(email_tasks.send_email_generic, "_orig_run")
    func = getattr(orig, "__func__", orig)
    func(None, recipient, subject, body)

    assert len(calls) == 1
    called_recipient, msg = calls[0]
    assert called_recipient == recipient
    assert msg["Subject"] == subject
    assert msg["From"] == sender_email
    assert body in msg.get_payload()


def test_send_email_generic_propagates_exception(monkeypatch):
    def fake_send(recipient, message):
        raise RuntimeError("smtp fail")

    monkeypatch.setattr("server.app.email_platform.email_tasks.send_email", fake_send)

    with pytest.raises(RuntimeError):
        orig = getattr(email_tasks.send_email_generic, "_orig_run")
        func = getattr(orig, "__func__", orig)
        func(None, "to@example.com", "s", "b")
