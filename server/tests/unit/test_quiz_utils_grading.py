import pytest
from fastapi import HTTPException

from server.app.quiz.utils.grading import grade_answers


def test_grade_answers_mock():
  payload = [
    {
      "question": "Q",
      "user_answer": "A",
      "correct_answer": "A",
      "question_type": "multichoice",
    }
  ]
  result = grade_answers(payload, source="mock")
  assert isinstance(result, list)


def test_grade_answers_invalid_source():
  with pytest.raises(HTTPException):
    grade_answers([], source="bad")
