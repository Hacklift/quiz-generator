from server.app.share import share_tasks


def test_send_email_generic(monkeypatch):
  calls = {}

  def fake_send_email(recipient, msg):
    calls["recipient"] = recipient
    calls["subject"] = msg["Subject"]

  monkeypatch.setattr(share_tasks, "send_email", fake_send_email)
  monkeypatch.setattr(share_tasks, "sender_email", "no-reply@test")

  share_tasks.send_email_generic("a@b.com", "Subject", "Body")
  assert calls["recipient"] == "a@b.com"
  assert calls["subject"] == "Subject"
