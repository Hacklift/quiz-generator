import pytest
from fastapi import HTTPException
from server.app.quiz.utils.questions import get_questions
from server.app.quiz.models.quiz_models import QuizRequest


@pytest.mark.asyncio
async def test_get_questions_invalid_question_type_returns_400(monkeypatch):
    async def fake_generate_quiz_with_huggingface(_payload):
        raise Exception("HF unavailable")

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        fake_generate_quiz_with_huggingface,
    )
    req = QuizRequest(
        profession="Test",
        num_questions=2,
        question_type="invalid-type",
        difficulty_level="easy",
        audience_type="students",
    )

    with pytest.raises(HTTPException) as exc:
        await get_questions(req)

    assert exc.value.status_code == 400
