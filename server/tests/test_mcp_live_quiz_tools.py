import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "smtp.example.com")
os.environ.setdefault("email_port", "587")
os.environ.setdefault("share_url", "http://localhost:3000")
os.environ.setdefault("db_name", "test")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")

import server.app.mcp.tools.live_quiz_tools as live_quiz_tools


ACTIVE_EXPIRES_AT = datetime.now(timezone.utc) + timedelta(hours=2)


def active_quiz(**overrides: Any) -> dict[str, Any]:
    quiz = {
        "_id": "quiz-1",
        "title": "Systems Design",
        "owner_user_id": "user-1",
        "live_quiz_enabled": True,
        "access_code": "ABC123",
        "time_limit_minutes": 20,
        "access_code_expires_at": ACTIVE_EXPIRES_AT,
    }
    quiz.update(overrides)
    return quiz


class FakeEmailService:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    async def send_email(self, **kwargs):
        self.calls.append(kwargs)
        return {"ok": True}


class FailingLiveQuizSessionService:
    def __init__(self, *_args, **_kwargs):
        pass

    async def generate_access_code(self, **_kwargs):
        raise AssertionError("generate_access_code should not be called when an active link exists")


class CreatingLiveQuizSessionService:
    def __init__(self, *_args, **_kwargs):
        self.calls: list[dict[str, Any]] = []

    async def generate_access_code(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "quiz_id": kwargs["quiz_id"],
            "access_code": "NEW123",
            "time_limit_minutes": kwargs["time_limit_minutes"],
            "access_code_expires_at": kwargs["access_code_expires_at"],
        }


@pytest.mark.asyncio
async def test_live_quiz_create_access_link_reuses_active_existing_link(monkeypatch):
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(), "user-1")),
    )
    monkeypatch.setattr(live_quiz_tools, "LiveQuizSessionService", FailingLiveQuizSessionService)

    result = await live_quiz_tools.live_quiz_create_access_link(
        quiz_id="quiz-1",
        duration=45,
    )

    assert result["found"] is True
    assert result["reused_existing"] is True
    assert result["access_code"] == "ABC123"
    assert result["live_quiz_link"] == "http://localhost:3000/quiz-access/ABC123"
    assert result["time_limit_minutes"] == 20


@pytest.mark.asyncio
async def test_live_quiz_create_access_link_creates_when_existing_link_expired(monkeypatch):
    expired_quiz = active_quiz(access_code_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    service = CreatingLiveQuizSessionService()
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((expired_quiz, "user-1")),
    )
    monkeypatch.setattr(live_quiz_tools, "_live_quiz_repository", lambda: object())
    monkeypatch.setattr(live_quiz_tools, "LiveQuizSessionService", lambda *_args, **_kwargs: service)

    result = await live_quiz_tools.live_quiz_create_access_link(
        quiz_id="quiz-1",
        duration=30,
        expires_in_hours=3,
    )

    assert result["reused_existing"] is False
    assert result["access_code"] == "NEW123"
    assert result["live_quiz_link"] == "http://localhost:3000/quiz-access/NEW123"
    assert service.calls[0]["quiz_id"] == "quiz-1"
    assert service.calls[0]["creator_id"] == "user-1"
    assert service.calls[0]["time_limit_minutes"] == 30


@pytest.mark.asyncio
async def test_live_quiz_create_access_link_requires_positive_duration(monkeypatch):
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(access_code=None, live_quiz_enabled=False), "user-1")),
    )

    with pytest.raises(ValueError, match="duration must be positive"):
        await live_quiz_tools.live_quiz_create_access_link(
            quiz_id="quiz-1",
            duration=0,
        )


@pytest.mark.asyncio
async def test_live_quiz_ensure_access_link_reuses_active_without_duration(monkeypatch):
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(), "user-1")),
    )
    monkeypatch.setattr(live_quiz_tools, "LiveQuizSessionService", FailingLiveQuizSessionService)

    result = await live_quiz_tools.live_quiz_ensure_access_link(quiz_id="quiz-1")

    assert result["found"] is True
    assert result["requires_duration"] is False
    assert result["reused_existing"] is True
    assert result["live_quiz_link"] == "http://localhost:3000/quiz-access/ABC123"


@pytest.mark.asyncio
async def test_live_quiz_ensure_access_link_requires_duration_when_no_active_link(monkeypatch):
    inactive_quiz = active_quiz(live_quiz_enabled=False, access_code=None, access_code_expires_at=None)
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((inactive_quiz, "user-1")),
    )

    result = await live_quiz_tools.live_quiz_ensure_access_link(quiz_id="quiz-1")

    assert result["found"] is False
    assert result["requires_duration"] is True
    assert result["quiz_id"] == "quiz-1"


@pytest.mark.asyncio
async def test_live_quiz_ensure_access_link_creates_when_duration_supplied(monkeypatch):
    inactive_quiz = active_quiz(live_quiz_enabled=False, access_code=None, access_code_expires_at=None)
    service = CreatingLiveQuizSessionService()
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((inactive_quiz, "user-1")),
    )
    monkeypatch.setattr(live_quiz_tools, "_live_quiz_repository", lambda: object())
    monkeypatch.setattr(live_quiz_tools, "LiveQuizSessionService", lambda *_args, **_kwargs: service)

    result = await live_quiz_tools.live_quiz_ensure_access_link(quiz_id="quiz-1", duration=15)

    assert result["found"] is True
    assert result["requires_duration"] is False
    assert result["reused_existing"] is False
    assert result["live_quiz_link"] == "http://localhost:3000/quiz-access/NEW123"
    assert service.calls[0]["time_limit_minutes"] == 15


@pytest.mark.asyncio
async def test_live_quiz_send_invites_sends_to_deduped_recipients(monkeypatch):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(), "user-1")),
    )
    monkeypatch.setattr(live_quiz_tools, "build_email_service", lambda _background: email_service)

    result = await live_quiz_tools.live_quiz_send_invites(
        quiz_id="quiz-1",
        recipient_emails=["One@example.com", "one@example.com", "two@example.com"],
        live_quiz_link="http://localhost:3000/quiz-access/ABC123",
        message="Join this quiz.",
    )

    assert result["sent_count"] == 2
    assert result["failed_count"] == 0
    assert result["sent"] == ["one@example.com", "two@example.com"]
    assert [call["to"] for call in email_service.calls] == ["one@example.com", "two@example.com"]
    assert all(call["template_id"] == "live_quiz_invite" for call in email_service.calls)
    assert all(call["purpose"] == "live_quiz_invite" for call in email_service.calls)
    assert email_service.calls[0]["template_vars"]["link"] == "http://localhost:3000/quiz-access/ABC123"
    assert email_service.calls[0]["template_vars"]["message"] == "Join this quiz."


@pytest.mark.asyncio
async def test_live_quiz_send_invites_rejects_recipient_cap(monkeypatch):
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(), "user-1")),
    )
    recipients = [f"user{i}@example.com" for i in range(live_quiz_tools.MAX_LIVE_QUIZ_INVITE_RECIPIENTS + 1)]

    with pytest.raises(ValueError, match="limited to"):
        await live_quiz_tools.live_quiz_send_invites(
            quiz_id="quiz-1",
            recipient_emails=recipients,
        )


@pytest.mark.asyncio
async def test_live_quiz_send_invites_rejects_invalid_email(monkeypatch):
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(), "user-1")),
    )

    with pytest.raises(ValidationError):
        await live_quiz_tools.live_quiz_send_invites(
            quiz_id="quiz-1",
            recipient_emails=["not-an-email"],
        )


@pytest.mark.asyncio
async def test_live_quiz_send_invites_requires_active_live_link(monkeypatch):
    inactive_quiz = active_quiz(live_quiz_enabled=False, access_code=None, access_code_expires_at=None)
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((inactive_quiz, "user-1")),
    )

    with pytest.raises(ValueError, match="Create a live quiz link"):
        await live_quiz_tools.live_quiz_send_invites(
            quiz_id="quiz-1",
            recipient_emails=["one@example.com"],
        )


@pytest.mark.asyncio
async def test_live_quiz_send_invites_rejects_stale_supplied_link(monkeypatch):
    monkeypatch.setattr(
        live_quiz_tools,
        "_owned_quiz_for_context",
        lambda _quiz_id: _async_return((active_quiz(), "user-1")),
    )

    with pytest.raises(ValueError, match="no longer current"):
        await live_quiz_tools.live_quiz_send_invites(
            quiz_id="quiz-1",
            recipient_emails=["one@example.com"],
            live_quiz_link="http://localhost:3000/quiz-access/OLD999",
        )


async def _async_return(value):
    return value
