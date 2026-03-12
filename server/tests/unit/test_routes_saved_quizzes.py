import pytest

from server.app.db.routes import saved_quizzes
from server.app.db.models.saved_quiz_model import SavedQuizModel


@pytest.mark.asyncio
async def test_saved_quizzes_routes(monkeypatch, dummy_user):
  async def fake_save_quiz(**_kwargs):
    return "qid"

  async def fake_get_saved_quizzes(**_kwargs):
    return [{"_id": "qid"}]

  async def fake_delete_saved_quiz(**_kwargs):
    return True

  async def fake_get_saved_quiz_by_id(_quiz_id, **_kwargs):
    return {"_id": _quiz_id, "user_id": dummy_user.id}

  monkeypatch.setattr(saved_quizzes, "save_quiz", fake_save_quiz)
  monkeypatch.setattr(saved_quizzes, "get_saved_quizzes", fake_get_saved_quizzes)
  monkeypatch.setattr(saved_quizzes, "delete_saved_quiz", fake_delete_saved_quiz)
  monkeypatch.setattr(saved_quizzes, "get_saved_quiz_by_id", fake_get_saved_quiz_by_id)

  payload = SavedQuizModel(
    title="T",
    question_type="multichoice",
    questions=[{"question": "Q1", "question_type": "multichoice"}],
  )
  created = await saved_quizzes.create_saved_quiz(payload, current_user=dummy_user)
  assert created["quiz_id"] == "qid"

  listed = await saved_quizzes.list_saved_quizzes(current_user=dummy_user)
  assert len(listed) == 1

  found = await saved_quizzes.get_saved_quiz("507f1f77bcf86cd799439011", current_user=dummy_user)
  assert found["_id"] == "507f1f77bcf86cd799439011"

  removed = await saved_quizzes.remove_saved_quiz("qid", current_user=dummy_user)
  assert removed["message"] == "Quiz deleted successfully"
