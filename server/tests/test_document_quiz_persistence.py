from types import SimpleNamespace

import pytest

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
