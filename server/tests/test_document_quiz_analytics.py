from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Response

from server.app.quiz.routes import document_quiz


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    original_enabled = document_quiz.limiter.enabled
    document_quiz.limiter.enabled = False
    try:
        yield
    finally:
        document_quiz.limiter.enabled = original_enabled


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("access_code_created", "expected_event_count"),
    [(True, 2), (False, 1)],
)
async def test_document_generation_records_live_event_only_for_new_activation(
    monkeypatch, access_code_created, expected_event_count
):
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    current_user = SimpleNamespace(
        id="user-1",
        persona_category="school",
        persona_user_type="teacher",
    )
    rag_result = SimpleNamespace(
        questions=[
            {
                "question": "What is a document?",
                "options": ["Text", "Sound"],
                "answer": "Text",
                "question_type": "multichoice",
            }
        ],
        title="Document quiz",
        description="Generated from text",
        retrieved_chunks=[],
        retrieval_query="document",
        rag_strategy="embedding_mmr",
        embedding_cache_hit=False,
    )
    recorder = AsyncMock()

    class LiveService:
        def __init__(self, _repository):
            pass

        async def generate_access_code(self, **kwargs):
            return {
                "_access_code_created": access_code_created,
                "access_code": "LIVE01",
                "access_code_expires_at": kwargs["access_code_expires_at"],
            }

    monkeypatch.setattr(
        document_quiz,
        "extract_text_from_pasted_content",
        lambda **_kwargs: SimpleNamespace(
            text="A sufficiently long source document for a generated quiz.",
            title="Source",
            source_document_type="text",
            source_document_name="pasted-text",
            source_characters=56,
        ),
    )
    monkeypatch.setattr(
        document_quiz,
        "split_text_into_chunks",
        lambda _text: [SimpleNamespace(text="source", index=0)],
    )
    monkeypatch.setattr(
        document_quiz,
        "generate_document_quiz_with_rag",
        AsyncMock(return_value=rag_result),
    )
    monkeypatch.setattr(
        document_quiz,
        "save_ai_generated_quiz",
        AsyncMock(return_value={"quiz_id": "quiz-1"}),
    )
    monkeypatch.setattr(document_quiz, "LiveQuizSessionService", LiveService)
    monkeypatch.setattr(document_quiz, "record_product_event_safely", recorder)

    result = await document_quiz.generate_document_quiz(
        request=MagicMock(),
        response=Response(),
        question_type="multichoice",
        num_questions=1,
        difficulty_level="easy",
        audience_type="students",
        custom_instruction=None,
        token=None,
        document_title=None,
        document_text="source text",
        focus_topic=None,
        live_quiz_enabled=True,
        time_limit_minutes=20,
        access_code_expires_at=expiration,
        document_file=None,
        current_user=current_user,
    )

    assert result.live_quiz_enabled is True
    assert result.access_code == "LIVE01"
    assert recorder.await_count == expected_event_count
    event_types = [call.kwargs["event_type"] for call in recorder.await_args_list]
    assert event_types.count("quiz_generated") == 1
    assert event_types.count("live_quiz_enabled") == int(access_code_created)
