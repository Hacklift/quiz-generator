import pytest

from server.app.quiz.utils import questions as q
from server.app.quiz.models.quiz_models import QuizRequest


@pytest.mark.asyncio
async def test_get_questions_fallback_to_mock(monkeypatch):
  async def _raise(_payload):
    raise Exception("down")

  monkeypatch.setattr(q, "generate_quiz_with_huggingface", _raise)

  req = QuizRequest(
    profession="Engineer",
    num_questions=2,
    question_type="multichoice",
    difficulty_level="easy",
    audience_type="students",
    custom_instruction="",
  )
  result = await q.get_questions(req)
  assert result["source"] == "mock"
  assert len(result["questions"]) == 2


@pytest.mark.asyncio
async def test_get_questions_invalid_type(monkeypatch):
  async def _raise(_payload):
    raise Exception("down")

  monkeypatch.setattr(q, "generate_quiz_with_huggingface", _raise)

  req = QuizRequest(
    profession="Engineer",
    num_questions=2,
    question_type="invalid-type",
    difficulty_level="easy",
    audience_type="students",
    custom_instruction="",
  )
  with pytest.raises(Exception):
    await q.get_questions(req)
