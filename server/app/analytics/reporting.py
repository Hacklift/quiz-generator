from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Iterable

from server.app.users.persona import persona_pair_is_valid


def normalize_event_persona(category: Any, user_type: Any) -> tuple[str, str]:
    if category and user_type and persona_pair_is_valid(category, user_type):
        return category.strip().lower(), user_type.strip().lower()
    return "unset", "unset"


def period_key(value: datetime, granularity: str) -> str:
    if granularity == "day":
        return value.strftime("%Y-%m-%d")
    if granularity == "week":
        monday = value - timedelta(days=value.weekday())
        return monday.strftime("%Y-%m-%d")
    if granularity == "month":
        return value.strftime("%Y-%m")
    raise ValueError("granularity must be day, week, or month")


def aggregate_persona_events(
    auth_events: Iterable[dict[str, Any]],
    product_events: Iterable[dict[str, Any]],
    granularity: str,
) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {"signups": 0, "generations": 0}
    )
    for event in auth_events:
        persona = (event.get("metadata") or {}).get("persona") or {}
        category, user_type = normalize_event_persona(
            persona.get("category"), persona.get("user_type")
        )
        counts[(period_key(event["created_at"], granularity), category, user_type)][
            "signups"
        ] += 1

    for event in product_events:
        category, user_type = normalize_event_persona(
            event.get("persona_category"), event.get("persona_user_type")
        )
        counts[(period_key(event["created_at"], granularity), category, user_type)][
            "generations"
        ] += 1

    return [
        {
            "period": period,
            "persona_category": category,
            "persona_user_type": user_type,
            **counts[(period, category, user_type)],
        }
        for period, category, user_type in sorted(counts)
    ]
