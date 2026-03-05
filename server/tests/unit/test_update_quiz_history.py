import pytest
from server.app.db.crud import update_quiz_history as uq


@pytest.mark.asyncio
async def test_update_quiz_history_inserts(monkeypatch, fake_quiz_history_collection):
  monkeypatch.setattr(uq, "quiz_history_collection", fake_quiz_history_collection)
  quiz_id = await uq.update_quiz_history({"user_id": "u1", "questions": []})
  assert quiz_id is not None
  assert len(fake_quiz_history_collection.docs) == 1


@pytest.mark.asyncio
async def test_get_quiz_history(monkeypatch, fake_quiz_history_collection):
  monkeypatch.setattr(uq, "quiz_history_collection", fake_quiz_history_collection)
  await uq.update_quiz_history({"user_id": "u1", "questions": []})
  quizzes = await uq.get_quiz_history("u1")
  assert len(quizzes) == 1
