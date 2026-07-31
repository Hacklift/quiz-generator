from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ACTIVE_USER_STATUSES = {"pending_verification", "active"}
BLOCKED_USER_STATUSES = {"suspended", "deleted"}
USER_SCHEMA_VERSION = 2
DEFAULT_AVATAR_COLOR = "#143E6F"


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def normalize_username(username: str) -> str:
    return username.strip().casefold()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_profile_value(user: dict[str, Any], key: str, default: Any = None) -> Any:
    profile = user.get("profile") or {}
    if isinstance(profile, dict) and key in profile:
        return profile.get(key)
    return user.get(key, default)


def build_profile(
    *,
    full_name: str | None = None,
    bio: str | None = None,
    location: str | None = None,
    website: str | None = None,
    avatar_color: str | None = None,
    persona: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Imported lazily: persona.py imports now_utc from this module.
    from server.app.users.persona import build_persona

    return {
        "full_name": full_name,
        "bio": bio,
        "location": location,
        "website": website,
        "avatar_color": avatar_color or DEFAULT_AVATAR_COLOR,
        "persona": persona if persona is not None else build_persona(),
    }


def default_user_status(is_verified: bool = False) -> str:
    return "active" if is_verified else "pending_verification"


def coerce_user_status(user: dict[str, Any]) -> str:
    status = user.get("status")
    if status:
        return status
    if user.get("deleted_at"):
        return "deleted"
    return default_user_status(bool(user.get("is_verified", False)))
