import importlib
import os

from server.app.email_platform.renderer import render_email
from server.app.email_platform.platform_email_utils import sender_email


def test_render_quiz_link():
    title = "T"
    desc = "D"
    link = "http://x"
    msg = render_email("quiz_link", "user@example.com", {"title": title, "description": desc, "link": link})
    assert msg["Subject"] == f"Check out this quiz: {title}"
    assert msg["To"] == "user@example.com"
    assert msg["From"] == sender_email
    assert msg.get_content_type() == "text/plain"
    body = msg.get_payload()
    assert title in body
    assert desc in body
    assert link in body


def test_render_verification_contains_link_and_code():
    code = "999"
    token = "ttt"
    msg = render_email("verification", "user@example.com", {"code": code, "token": token})
    assert msg["To"] == "user@example.com"
    assert msg["From"] == sender_email
    body = msg.get_payload()
    assert code in body
    assert "verify-email" in body or token in body


def test_render_password_reset_contains_link_and_code():
    code = "321"
    token = "tok"
    msg = render_email("password_reset", "user@example.com", {"code": code, "token": token})
    assert msg["To"] == "user@example.com"
    assert msg["From"] == sender_email
    body = msg.get_payload()
    assert code in body
    assert "reset-password" in body or token in body


def test_render_custom_template():
    subj = "Hi"
    body_text = "Body here"
    msg = render_email("custom", "user@example.com", {"subject": subj, "body": body_text})
    assert msg["Subject"] == subj
    assert msg["To"] == "user@example.com"
    assert msg["From"] == sender_email
    assert msg.get_content_type() == "text/plain"
    assert body_text in msg.get_payload()


def test_render_quiz_link_missing_vars_raises_keyerror():
    try:
        render_email("quiz_link", "user@example.com", {"description": "D", "link": "http://x"})
    except KeyError:
        return
    raise AssertionError("Expected KeyError for missing template var 'title'")


def test_renderer_unknown_template_returns_default_notification():
    msg = render_email("non_existent_template", "a@test.com", {})
    assert msg["Subject"] == "Notification"
    assert msg.get_payload() == ""


def test_renderer_uses_allowed_origins_for_links(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com/")
    import server.app.email_platform.renderer as renderer_module
    importlib.reload(renderer_module)
    msg = renderer_module.render_email("verification", "user@example.com", {"code": "999", "token": "tok"})
    body = msg.get_payload()
    assert "https://example.com/auth/verify-email/?token=tok" in body
