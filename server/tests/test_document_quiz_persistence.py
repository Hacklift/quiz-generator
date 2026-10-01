import os
from types import SimpleNamespace

import pytest

# Keep this focused route module independently runnable; importing the route
# resolves application settings before the test has a chance to mock services.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EMAIL_SENDER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("EMAIL_HOST", "smtp.example.com")
os.environ.setdefault("EMAIL_PORT", "587")
os.environ.setdefault("SHARE_URL", "http://localhost:3000")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/quizApp_test")
os.environ.setdefault("ASSISTANT_INTERNAL_MCP_SECRET", "test-internal-mcp-secret")

from server.app.quiz.routes import document_quiz


@pytest.mark.asyncio
async def test_guest_document_generation_does_not_persist_a_canonical_quiz(monkeypatch):
    """Guests receive an ephemeral response, matching ordinary generation."""

    async def generate_document_quiz_with_rag(**_kwargs):
        return SimpleNamespace(
            title="Guest material quiz",
            description="Generated from pasted text",
            retrieval_query="guest material",
            retrieved_chunks=[SimpleNamespace()],
            questions=[
                {
                    "question": "What is the key fact?",
                    "options": ["A", "B"],
                    "question_type": "multichoice",
                    "answer": "A",
                }
            ],
            rag_strategy="embedding_mmr",
            embedding_cache_hit=False,
        )

    async def fail_if_persisted(_payload):
        raise AssertionError("guest document generation must not persist a canonical quiz")

    monkeypatch.setattr(
        document_quiz,
        "generate_document_quiz_with_rag",
        generate_document_quiz_with_rag,
    )
    monkeypatch.setattr(document_quiz, "save_ai_generated_quiz", fail_if_persisted)

    response = await document_quiz.generate_document_quiz.__wrapped__(
        request=None,
        response=None,
        question_type="multichoice",
        num_questions=1,
        difficulty_level="easy",
        audience_type="students",
        custom_instruction=None,
        token=None,
        document_title=None,
        document_text="This material contains enough text to create a guest quiz.",
        focus_topic=None,
        live_quiz_enabled=False,
        time_limit_minutes=None,
        access_code_expires_at=None,
        document_file=None,
        current_user=None,
        organization=None,
    )

    assert response.quiz_id is None
    assert response.questions[0].answer == "A"


@pytest.mark.asyncio
async def test_unscoped_authenticated_document_generation_degrades_to_ephemeral_guest(monkeypatch):
    """An optional-auth tenant failure must never create an unscoped quiz."""

    async def generate_document_quiz_with_rag(**kwargs):
        assert kwargs["user_id"] is None
        return SimpleNamespace(
            title="Unscoped material quiz",
            description="Generated from pasted text",
            retrieval_query="guest material",
            retrieved_chunks=[SimpleNamespace()],
            questions=[
                {
                    "question": "Question?",
                    "options": ["A", "B"],
                    "answer": "A",
                    "question_type": "multichoice",
                }
            ],
            rag_strategy="embedding_mmr",
            embedding_cache_hit=False,
        )

    async def fail_if_persisted(_payload):
        raise AssertionError("an unscoped authenticated request must remain ephemeral")

    monkeypatch.setattr(document_quiz, "generate_document_quiz_with_rag", generate_document_quiz_with_rag)
    monkeypatch.setattr(document_quiz, "save_ai_generated_quiz", fail_if_persisted)

    response = await document_quiz.generate_document_quiz.__wrapped__(
        request=None,
        response=None,
        question_type="multichoice",
        num_questions=1,
        difficulty_level="easy",
        audience_type="students",
        custom_instruction=None,
        token=None,
        document_title=None,
        document_text="This material contains enough text to create a guest quiz.",
        focus_topic=None,
        live_quiz_enabled=False,
        time_limit_minutes=None,
        access_code_expires_at=None,
        document_file=None,
        current_user=SimpleNamespace(id="user-without-an-active-organization"),
        organization=None,
    )

    assert response.quiz_id is None
