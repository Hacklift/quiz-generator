import os

import pytest
from bson import ObjectId

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "smtp.example.com")
os.environ.setdefault("email_port", "587")
os.environ.setdefault("share_url", "http://localhost:3000")
os.environ.setdefault("db_name", "test")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")
os.environ.setdefault("ASSISTANT_INTERNAL_MCP_SECRET", "test-internal-mcp-secret")

from server.app.quiz.repositories.v2.models.quiz_models import (
    QuizDocumentV2,
    QuizQuestionV2,
    QuizSourceV2,
    QuizTypeV2,
)
from server.app.quiz.services.quiz_answer_service import QuizAnswerKeyService


class FakeLibraryService:
    def __init__(self, quiz):
        self.quiz = quiz

    async def get_owned_or_library_quiz(self, *, user_id: str, quiz_id: str):
        return self.quiz


def make_quiz(*, quiz_type: QuizTypeV2) -> QuizDocumentV2:
    return QuizDocumentV2(
        _id=ObjectId(),
        title="Systems Design",
        quiz_type=quiz_type,
        owner_user_id="user-1",
        source=QuizSourceV2.AI,
        questions=[
            QuizQuestionV2(
                question="What is a circuit breaker?",
                correct_answer="A fault isolation pattern.",
                options=None,
            )
        ],
    )


@pytest.mark.asyncio
async def test_answer_key_returns_stored_answers_for_multichoice():
    service = QuizAnswerKeyService(
        library_service=FakeLibraryService(make_quiz(quiz_type=QuizTypeV2.MULTICHOICE)),
    )

    result = await service.get_answer_key(user_id="user-1", quiz_id="quiz-1")

    assert result["title"] == "Systems Design"
    assert result["model_generated"] is False
    assert result["answers"][0]["answer"] == "A fault isolation pattern."
    assert result["answers"][0]["source"] == "stored"


@pytest.mark.asyncio
async def test_answer_key_uses_model_guidance_for_open_response(monkeypatch):
    service = QuizAnswerKeyService(
        library_service=FakeLibraryService(make_quiz(quiz_type=QuizTypeV2.OPEN_ENDED)),
    )

    async def fake_guidance(_quiz):
        return {1: "A circuit breaker prevents cascading failures by stopping calls to unhealthy dependencies."}

    monkeypatch.setattr(service, "_generate_open_response_answers", fake_guidance)

    result = await service.get_answer_key(user_id="user-1", quiz_id="quiz-1")

    assert result["model_generated"] is True
    assert result["answers"][0]["source"] == "model_generated"
    assert "cascading failures" in result["answers"][0]["answer"]


@pytest.mark.asyncio
async def test_answer_key_rejects_unavailable_quiz():
    service = QuizAnswerKeyService(library_service=FakeLibraryService(None))

    with pytest.raises(ValueError, match="not available"):
        await service.get_answer_key(user_id="user-1", quiz_id="quiz-1")
