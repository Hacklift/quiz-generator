from __future__ import annotations

import re
from typing import Any


AUTH_REQUIRED_CODE = "AUTH_REQUIRED"
VERIFICATION_REQUIRED_CODE = "VERIFICATION_REQUIRED"


def assistant_policy_error_detail(*, code: str, tool_name: str) -> dict[str, str]:
    return {"code": code, "tool_name": tool_name}


def user_message_for_policy_error(detail: Any) -> str | None:
    if not isinstance(detail, dict):
        return None

    code = detail.get("code")
    tool_name = str(detail.get("tool_name") or "")
    if code == AUTH_REQUIRED_CODE:
        return auth_required_message(tool_name)
    if code == VERIFICATION_REQUIRED_CODE:
        return verification_required_message(tool_name)
    return None


def auth_required_message(tool_name: str) -> str:
    if tool_name == "quiz_generate":
        return "Please log in to generate quizzes."
    if tool_name in {"quiz_export_link", "share_create_link", "share_send_email", "live_quiz_send_invites"}:
        return "Please log in to download, share, or send quiz links."
    if tool_name.startswith("folder_") or tool_name.startswith("library_") or tool_name.startswith("saved_quiz_"):
        return "Please log in to access your folders, saved quizzes, history, downloads, sharing, and other personal assistant features."
    if tool_name.startswith("notification_"):
        return "Please log in to access your notifications."
    return "Please log in to use this assistant action."


def verification_required_message(tool_name: str) -> str:
    if tool_name == "quiz_generate":
        return "Please verify your email before generating quizzes."
    return "Please verify your email before using this assistant action."


def tool_error_message(tool_name: str, data: dict[str, Any]) -> str:
    raw_error = _extract_error_text(data)
    clean_error = _clean_internal_error(raw_error)

    if _is_expired_session_error(clean_error):
        return "Your session expired. Please log in again, then retry this request."

    question_limit = _question_limit_from_error(clean_error)
    if tool_name == "quiz_generate" and question_limit is not None:
        return f"This quiz can have up to {question_limit} questions. Try again with {question_limit} or fewer."

    if "authentication" in clean_error.casefold() or "not authenticated" in clean_error.casefold():
        return auth_required_message(tool_name)
    if "verification" in clean_error.casefold() or "verify your email" in clean_error.casefold():
        return verification_required_message(tool_name)

    if "not found" in clean_error.casefold():
        return _not_found_message(tool_name, clean_error)

    if tool_name == "quiz_generate":
        return f"I could not generate the quiz: {clean_error}"
    if tool_name == "quiz_export_link":
        return f"I could not prepare the quiz download: {clean_error}"
    if tool_name in {"share_create_link", "share_send_email"}:
        return f"I could not complete the sharing request: {clean_error}"
    if tool_name in {"live_quiz_get_access_link", "live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
        return f"I could not prepare the live quiz link: {clean_error}"
    if tool_name == "live_quiz_send_invites":
        return f"I could not send the live quiz invites: {clean_error}"
    if tool_name.startswith("folder_"):
        return f"I could not complete the folder request: {clean_error}"
    if tool_name.startswith("library_") or tool_name.startswith("saved_quiz_"):
        return f"I could not complete the library request: {clean_error}"
    return f"I could not complete the request: {clean_error}"


def _extract_error_text(data: dict[str, Any]) -> str:
    error = (
        data.get("error")
        or data.get("message")
        or data.get("detail")
        or data.get("result")
        or "The request could not be completed."
    )
    if isinstance(error, list):
        return "; ".join(str(item) for item in error)
    if isinstance(error, dict):
        detail = error.get("detail") or error.get("message") or error.get("error")
        return str(detail or error)
    return str(error)


def _clean_internal_error(error: str) -> str:
    cleaned = error.strip()
    cleaned = re.sub(r"^Error executing tool\s+[A-Za-z0-9_]+:\s*", "", cleaned)
    cleaned = re.sub(r"^\d{3}:\s*", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned or "The request could not be completed."


def _question_limit_from_error(error: str) -> int | None:
    match = re.search(r"limited to\s+(\d+)\s+questions?", error, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"up to\s+(\d+)\s+questions?", error, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _is_expired_session_error(error: str) -> bool:
    normalized = error.casefold()
    return "token has expired" in normalized or "signature has expired" in normalized


def _not_found_message(tool_name: str, error: str) -> str:
    if tool_name in {"live_quiz_get_access_link", "live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
        return "I could not find that quiz in your library or history."
    if tool_name.startswith("folder_"):
        return "I could not find the requested folder or quiz in your folders."
    if tool_name.startswith("library_") or tool_name.startswith("saved_quiz_"):
        return "I could not find that quiz in your library or history."
    return error
