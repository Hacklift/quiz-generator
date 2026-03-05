import pytest

from server.app.share.routes import share_routes
from server.app.share.routes.share_schemas import ShareEmailRequest


class DummyEmail:
  async def send_email(self, **_kwargs):
    return {"ok": True}


@pytest.mark.asyncio
async def test_share_routes(monkeypatch):
  async def fake_list_quizzes(_collection):
    return [type("Q", (), {"id": "qid", "title": "T", "description": "D"})()]

  async def fake_get_quiz(_collection, _qid):
    return type("Q", (), {"title": "T", "description": "D"})()

  monkeypatch.setattr(share_routes, "list_quizzes", fake_list_quizzes)
  monkeypatch.setattr(share_routes, "get_quiz", fake_get_quiz)
  monkeypatch.setattr(share_routes, "get_quizzes_collection", lambda: None)

  quiz = await share_routes.get_random_quiz_id(quizzes_collection=None)
  assert quiz.title == "T"

  link = await share_routes.get_share_link("qid")
  assert "link" in link

  req = ShareEmailRequest(quiz_id="qid", recipient_email="a@b.com", shareableLink="x")
  res = await share_routes.share_quiz_via_email(req, email_svc=DummyEmail())
  assert res["message"] == "Email sent successfully!"
