import pytest

from server.app.db.routes import save_quiz_history, get_quiz_history
from server.app.db.models.quiz_history_models import QuizHistoryModel


@pytest.mark.asyncio
async def test_quiz_history_routes(monkeypatch, dummy_user):
  async def fake_update_quiz_history(_data):
    return "qid"

  async def fake_get_quiz_history(_user_id):
    return [{"_id": "qid"}]

  monkeypatch.setattr(save_quiz_history, "update_quiz_history", fake_update_quiz_history)
  monkeypatch.setattr(get_quiz_history, "get_quiz_history", fake_get_quiz_history)

  payload = QuizHistoryModel(
    question_type="multichoice",
    questions=[{"question": "Q1", "answer": "A1", "question_type": "multichoice"}],
  )

  saved = await save_quiz_history.save_quiz(payload, current_user=dummy_user)
  assert saved["quiz_id"] == "qid"

  listed = await get_quiz_history.get_user_quiz_history(current_user=dummy_user)
  assert listed == [{"_id": "qid"}]
