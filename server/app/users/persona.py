"""Persona slugs and normalisation.

This module owns the *slugs* only. Labels, descriptions and generation
defaults live on the client in client/src/shared/config/persona.ts —
tests/test_persona_taxonomy.py fails if the two drift, so a slug change
means editing both files in the same PR.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from server.app.users.identity import now_utc


PERSONA_SCHEMA_VERSION = 1

PERSONA_CATEGORIES = ("school", "corporate")

PERSONA_USER_TYPES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "school": ("teacher", "lecturer", "student", "parent"),
    "corporate": ("business", "employee", "hr"),
}

PERSONA_USER_TYPES = tuple(
    user_type
    for user_types in PERSONA_USER_TYPES_BY_CATEGORY.values()
    for user_type in user_types
)

# How a persona came to be set — used by #137 (adoption analytics).
PERSONA_SOURCES = ("onboarding", "profile", "inferred", "unset")

_CATEGORY_BY_USER_TYPE = {
    user_type: category
    for category, user_types in PERSONA_USER_TYPES_BY_CATEGORY.items()
    for user_type in user_types
}


def normalize_persona_category(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    return candidate if candidate in PERSONA_CATEGORIES else None


def normalize_persona_user_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    return candidate if candidate in PERSONA_USER_TYPES else None


def category_for_user_type(user_type: Any) -> str | None:
    normalized = normalize_persona_user_type(user_type)
    return _CATEGORY_BY_USER_TYPE.get(normalized) if normalized else None


def persona_pair_is_valid(category: Any, user_type: Any) -> bool:
    """True when the pair is both-empty, or a user type inside its category."""
    normalized_category = normalize_persona_category(category)
    normalized_user_type = normalize_persona_user_type(user_type)

    if normalized_category is None and normalized_user_type is None:
        return category in (None, "") and user_type in (None, "")
    if normalized_category is None or normalized_user_type is None:
        return False
    return _CATEGORY_BY_USER_TYPE[normalized_user_type] == normalized_category


def build_persona(
    *,
    category: str | None = None,
    user_type: str | None = None,
    source: str = "unset",
    set_at: datetime | None = None,
) -> dict[str, Any]:
    """Persona sub-document factory, mirroring identity.build_profile."""
    normalized_user_type = normalize_persona_user_type(user_type)
    normalized_category = (
        normalize_persona_category(category)
        or category_for_user_type(normalized_user_type)
    )

    if normalized_user_type is None:
        normalized_category = normalize_persona_category(category)

    resolved_source = source if source in PERSONA_SOURCES else "unset"
    if normalized_user_type is None and resolved_source != "unset":
        resolved_source = "unset"

    return {
        "category": normalized_category,
        "user_type": normalized_user_type,
        "set_at": set_at if normalized_user_type else None,
        "source": resolved_source,
    }


def get_persona(user: dict[str, Any]) -> dict[str, Any]:
    """Tolerant reader for legacy docs, mirroring identity.get_profile_value."""
    profile = user.get("profile") or {}
    persona = profile.get("persona") if isinstance(profile, dict) else None
    if not isinstance(persona, dict):
        return build_persona()

    return build_persona(
        category=persona.get("category"),
        user_type=persona.get("user_type"),
        source=persona.get("source") or "unset",
        set_at=persona.get("set_at"),
    )


def persona_update_fields(
    category: str | None,
    user_type: str | None,
    *,
    source: str = "profile",
) -> dict[str, Any]:
    """Dotted `$set` paths for a persona change; empty when nothing was sent."""
    if category is None and user_type is None:
        return {}

    persona = build_persona(
        category=category,
        user_type=user_type,
        source=source,
        set_at=now_utc(),
    )
    return {f"profile.persona.{key}": value for key, value in persona.items()}
