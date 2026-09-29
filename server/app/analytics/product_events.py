from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError

from server.app.users.identity import now_utc
from server.app.users.persona import analytics_persona_snapshot


logger = logging.getLogger(__name__)

QUIZ_GENERATED = "quiz_generated"
LIVE_QUIZ_ENABLED = "live_quiz_enabled"
RESULTS_EXPORTED = "results_exported"
PRODUCT_EVENT_TYPES = {QUIZ_GENERATED, LIVE_QUIZ_ENABLED, RESULTS_EXPORTED}


async def record_product_event(
    collection: AsyncIOMotorCollection,
    *,
    event_type: str,
    user_id: str,
    user: Any,
    quiz_id: str | None = None,
    export_format: str | None = None,
) -> None:
    """Persist a small event using persona resolved from a trusted user object."""
    if event_type not in PRODUCT_EVENT_TYPES:
        raise ValueError(f"Unsupported product event type: {event_type}")

    event = {
        "event_type": event_type,
        "user_id": str(user_id),
        **analytics_persona_snapshot(user),
        "created_at": now_utc(),
    }
    if quiz_id is not None:
        event["quiz_id"] = str(quiz_id)
    if export_format is not None:
        event["export_format"] = export_format

    try:
        await collection.insert_one(event)
    except PyMongoError as exc:
        logger.warning("Failed to record product event %s: %s", event_type, exc)
