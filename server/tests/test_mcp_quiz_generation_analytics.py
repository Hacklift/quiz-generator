from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import server.app.mcp.tools.quiz_tools as quiz_tools
from server.app.mcp.context import McpRequestContext


def _trusted_context():
    user = SimpleNamespace(
        id="user-1",
        persona_category="school",
        persona_user_type="teacher",
    )
    return McpRequestContext(
        user_id="user-1",
        is_authenticated=True,
        is_verified=True,
        role="user",
        user=user,
    )


@pytest.mark.asyncio
async def test_successful_mcp_generation_records_one_attributed_event(monkeypatch):
    context = _trusted_context()
    events = SimpleNamespace(insert_one=AsyncMock())
    history_service = SimpleNamespace(
        create_quiz_history=AsyncMock(
            return_value=SimpleNamespace(id="history-1", quiz_id="quiz-1")
        )
    )
    monkeypatch.setattr(quiz_tools, "get_mcp_request_context", AsyncMock(return_value=context))
    monkeypatch.setattr(
        quiz_tools,
        "get_questions",
        AsyncMock(
            return_value={
                "quiz_id": "quiz-1",
                "questions": [{"question": "Q", "answer": "A"}],
            }
        ),
    )
    monkeypatch.setattr(quiz_tools, "QuizUserLibraryService", lambda: history_service)
    monkeypatch.setattr(quiz_tools, "get_product_events_collection", lambda: events)

    result = await quiz_tools.quiz_generate("Physics", 1, "multichoice")

    assert result["quiz_id"] == "quiz-1"
    events.insert_one.assert_awaited_once()
    event = events.insert_one.await_args.args[0]
    assert event["event_type"] == "quiz_generated"
    assert event["user_id"] == "user-1"
    assert event["quiz_id"] == "quiz-1"
    assert event["origin"] == "mcp"
    assert event["persona_category"] == "school"
    assert event["persona_user_type"] == "teacher"


@pytest.mark.asyncio
async def test_failed_mcp_generation_does_not_record_event(monkeypatch):
    events = SimpleNamespace(insert_one=AsyncMock())
    monkeypatch.setattr(
        quiz_tools,
        "get_mcp_request_context",
        AsyncMock(return_value=_trusted_context()),
    )
    monkeypatch.setattr(
        quiz_tools,
        "get_questions",
        AsyncMock(side_effect=RuntimeError("generation failed")),
    )
    monkeypatch.setattr(quiz_tools, "get_product_events_collection", lambda: events)

    with pytest.raises(RuntimeError, match="generation failed"):
        await quiz_tools.quiz_generate("Physics", 1, "multichoice")

    events.insert_one.assert_not_awaited()
