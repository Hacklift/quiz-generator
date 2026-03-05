import pytest

from server.app.db.crud import saved_quiz_crud as sq


@pytest.mark.asyncio
async def test_save_and_get_saved_quizzes(monkeypatch, fake_saved_quizzes_collection):
  monkeypatch.setattr(sq, "collection", fake_saved_quizzes_collection)
  quiz_id = await sq.save_quiz(
    user_id="u1",
    title="Test",
    question_type="multichoice",
    questions=[{"question": "Q1", "answer": "A1", "question_type": "multichoice"}],
  )
  quizzes = await sq.get_saved_quizzes("u1")
  assert len(quizzes) == 1
  assert quizzes[0]["_id"] == quiz_id


@pytest.mark.asyncio
async def test_delete_saved_quiz(monkeypatch, fake_saved_quizzes_collection):
  monkeypatch.setattr(sq, "collection", fake_saved_quizzes_collection)
  quiz_id = await sq.save_quiz(
    user_id="u1",
    title="Test",
    question_type="multichoice",
    questions=[{"question": "Q1", "answer": "A1", "question_type": "multichoice"}],
  )
  deleted = await sq.delete_saved_quiz(quiz_id, "u1")
  assert deleted is True
