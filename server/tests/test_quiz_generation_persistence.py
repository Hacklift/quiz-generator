import pytest

from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.questions import get_questions


@pytest.mark.asyncio
async def test_authenticated_get_questions_persists_fallback_quiz(monkeypatch):
    saved_payloads = []

    async def _raise_hf(*args, **kwargs):
        raise Exception("mocked HF down")

    async def _save(quiz_payload):
        saved_payloads.append(quiz_payload)
        return {"quiz_id": "canonical-quiz-1"}

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        _raise_hf,
    )
    monkeypatch.setattr(
        "server.app.quiz.utils.questions.save_ai_generated_quiz",
        _save,
    )

    result = await get_questions(
        QuizRequest(
            profession="Engineer",
            num_questions=2,
            question_type="multichoice",
            difficulty_level="medium",
            audience_type="students",
            custom_instruction="",
        ),
        user_id="user-1",
    )

    assert result["quiz_id"] == "canonical-quiz-1"
    assert saved_payloads
    assert saved_payloads[0]["user_id"] == "user-1"
    assert saved_payloads[0]["questions"]
