from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import EmailStr, TypeAdapter

from server.app.core.config import settings
from server.app.db.core.connection import get_live_quiz_sessions_collection, get_quizzes_v2_collection
from server.app.email_platform.service import build_email_service
from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.repositories.live_session_repository import LiveQuizSessionRepository
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService
from server.app.quiz.services.live_session_service import LiveQuizSessionService


MAX_LIVE_QUIZ_INVITE_RECIPIENTS = 25
EMAIL_ADAPTER = TypeAdapter(EmailStr)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _frontend_live_quiz_link(access_code: str) -> str:
    return f"{settings.share_url.rstrip('/')}/quiz-access/{access_code.strip().upper()}"


def _serialize_datetime(value: datetime | None) -> str | None:
    return _as_utc(value).isoformat() if value else None


def _quiz_owner_id(quiz: dict[str, Any]) -> str | None:
    return quiz.get("owner_user_id") or quiz.get("created_by") or quiz.get("owner_id")


def _valid_existing_live_link(quiz: dict[str, Any]) -> dict[str, Any] | None:
    access_code = str(quiz.get("access_code") or "").strip().upper()
    expires_at = quiz.get("access_code_expires_at")
    time_limit_minutes = quiz.get("time_limit_minutes")
    if not quiz.get("live_quiz_enabled") or not access_code or not expires_at or not time_limit_minutes:
        return None
    if _as_utc(expires_at) <= _utc_now():
        return None
    return {
        "quiz_id": str(quiz.get("_id")),
        "title": quiz.get("title") or "Live Quiz",
        "access_code": access_code,
        "live_quiz_link": _frontend_live_quiz_link(access_code),
        "time_limit_minutes": int(time_limit_minutes),
        "access_code_expires_at": _serialize_datetime(expires_at),
        "reused_existing": True,
    }


def _live_quiz_repository() -> LiveQuizSessionRepository:
    return LiveQuizSessionRepository(
        get_quizzes_v2_collection(),
        get_live_quiz_sessions_collection(),
    )


async def _owned_quiz_for_context(quiz_id: str) -> tuple[dict[str, Any], str]:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    repository = _live_quiz_repository()
    quiz = await repository.get_quiz_by_id(quiz_id)
    if not quiz:
        saved_quiz = await QuizUserLibraryService().get_saved_quiz(
            user_id=context.user_id,
            saved_quiz_id=quiz_id,
        )
        if saved_quiz and saved_quiz.get("quiz_id"):
            quiz = await repository.get_quiz_by_id(str(saved_quiz["quiz_id"]))
    if not quiz:
        raise ValueError("Quiz not found")
    owner_id = _quiz_owner_id(quiz)
    if owner_id and owner_id != context.user_id:
        raise PermissionError("Quiz ownership is required to manage live quiz links.")
    return quiz, context.user_id or ""


def _parse_expiration(access_code_expires_at: str | None, expires_in_hours: int | None) -> datetime:
    if access_code_expires_at:
        normalized = access_code_expires_at.replace("Z", "+00:00")
        expires_at = datetime.fromisoformat(normalized)
        return _as_utc(expires_at)

    hours = int(expires_in_hours or 24)
    if hours <= 0:
        raise ValueError("expires_in_hours must be positive.")
    return _utc_now() + timedelta(hours=hours)


def _validate_recipients(recipient_emails: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for raw_email in recipient_emails:
        email = str(EMAIL_ADAPTER.validate_python(raw_email)).strip().lower()
        if email in seen:
            continue
        deduped.append(email)
        seen.add(email)

    if not deduped:
        raise ValueError("At least one recipient email is required.")
    if len(deduped) > MAX_LIVE_QUIZ_INVITE_RECIPIENTS:
        raise ValueError(
            f"Live quiz invites are limited to {MAX_LIVE_QUIZ_INVITE_RECIPIENTS} recipients at a time."
        )
    return deduped


async def live_quiz_get_access_link(quiz_id: str) -> dict[str, Any]:
    quiz, _user_id = await _owned_quiz_for_context(quiz_id)
    existing = _valid_existing_live_link(quiz)
    if not existing:
        return {
            "quiz_id": quiz_id,
            "title": quiz.get("title") or "Live Quiz",
            "found": False,
            "message": "No active live quiz link exists for this quiz.",
        }
    return {"found": True, **existing}


async def live_quiz_create_access_link(
    quiz_id: str,
    duration: int,
    access_code_expires_at: str | None = None,
    expires_in_hours: int | None = 24,
    regenerate: bool = False,
) -> dict[str, Any]:
    if int(duration) <= 0:
        raise ValueError("duration must be positive.")
    quiz, user_id = await _owned_quiz_for_context(quiz_id)
    existing = _valid_existing_live_link(quiz)
    if existing and not regenerate:
        return {"found": True, **existing}

    expires_at = _parse_expiration(access_code_expires_at, expires_in_hours)
    service = LiveQuizSessionService(_live_quiz_repository())
    response = await service.generate_access_code(
        quiz_id=quiz_id,
        access_code_expires_at=expires_at,
        creator_id=user_id,
        time_limit_minutes=int(duration),
    )
    return {
        "found": True,
        "quiz_id": response["quiz_id"],
        "title": quiz.get("title") or "Live Quiz",
        "access_code": response["access_code"],
        "live_quiz_link": _frontend_live_quiz_link(response["access_code"]),
        "duration": response["time_limit_minutes"],
        "time_limit_minutes": response["time_limit_minutes"],
        "access_code_expires_at": _serialize_datetime(response["access_code_expires_at"]),
        "reused_existing": False,
    }


async def live_quiz_ensure_access_link(
    quiz_id: str,
    duration: int | None = None,
    access_code_expires_at: str | None = None,
    expires_in_hours: int | None = 24,
    regenerate: bool = False,
) -> dict[str, Any]:
    quiz, user_id = await _owned_quiz_for_context(quiz_id)
    existing = _valid_existing_live_link(quiz)
    if existing and not regenerate:
        return {"found": True, "requires_duration": False, **existing}

    if duration is None:
        return {
            "found": False,
            "requires_duration": True,
            "quiz_id": str(quiz.get("_id")),
            "title": quiz.get("title") or "Live Quiz",
            "message": "Quiz duration is required to create a new live quiz link.",
        }

    if int(duration) <= 0:
        raise ValueError("duration must be positive.")

    expires_at = _parse_expiration(access_code_expires_at, expires_in_hours)
    service = LiveQuizSessionService(_live_quiz_repository())
    response = await service.generate_access_code(
        quiz_id=str(quiz["_id"]),
        access_code_expires_at=expires_at,
        creator_id=user_id,
        time_limit_minutes=int(duration),
    )
    return {
        "found": True,
        "requires_duration": False,
        "quiz_id": response["quiz_id"],
        "title": quiz.get("title") or "Live Quiz",
        "access_code": response["access_code"],
        "live_quiz_link": _frontend_live_quiz_link(response["access_code"]),
        "duration": response["time_limit_minutes"],
        "time_limit_minutes": response["time_limit_minutes"],
        "access_code_expires_at": _serialize_datetime(response["access_code_expires_at"]),
        "reused_existing": False,
    }


async def live_quiz_send_invites(
    quiz_id: str,
    recipient_emails: list[str],
    live_quiz_link: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    quiz, _user_id = await _owned_quiz_for_context(quiz_id)
    existing = _valid_existing_live_link(quiz)
    if not existing:
        raise ValueError("Create a live quiz link before sending invites.")
    link = existing["live_quiz_link"]
    if live_quiz_link and live_quiz_link != link:
        raise ValueError("The supplied live quiz link is no longer current. Use the active link for this quiz.")
    if not re.match(r"^https?://", link):
        raise ValueError("Live quiz link must be an absolute URL.")

    recipients = _validate_recipients(recipient_emails)
    email_service = build_email_service(None)
    sent: list[str] = []
    failed: list[dict[str, str]] = []

    for recipient in recipients:
        try:
            await email_service.send_email(
                to=recipient,
                template_id="live_quiz_invite",
                template_vars={
                    "title": str(quiz.get("title") or "Live Quiz"),
                    "link": link,
                    "message": message or "",
                    "time_limit_minutes": str(quiz.get("time_limit_minutes") or ""),
                    "access_code_expires_at": _serialize_datetime(quiz.get("access_code_expires_at")) or "",
                },
                purpose="live_quiz_invite",
                priority="default",
            )
            sent.append(recipient)
        except Exception as exc:  # pragma: no cover - adapter failures depend on runtime provider
            failed.append({"email": recipient, "error": str(exc)})

    if not sent:
        raise RuntimeError("Could not send any live quiz invites.")

    return {
        "message": "Live quiz invites sent.",
        "quiz_id": quiz_id,
        "title": quiz.get("title") or "Live Quiz",
        "live_quiz_link": link,
        "recipient_count": len(recipients),
        "sent_count": len(sent),
        "failed_count": len(failed),
        "sent": sent,
        "failed": failed,
    }
