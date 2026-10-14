from __future__ import annotations

import asyncio
import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError

from server.app.core.config import settings
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
    origin: str | None = None,
) -> None:
    """Best-effort event persistence using persona from a trusted user object."""
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
    if origin is not None:
        event["origin"] = origin

    try:
        await asyncio.wait_for(
            collection.insert_one(event),
            timeout=settings.PRODUCT_EVENT_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning(
            "Timed out recording product event %s after %.3fs",
            event_type,
            settings.PRODUCT_EVENT_TIMEOUT_SECONDS,
        )
    except PyMongoError as exc:
        logger.warning("Failed to record product event %s: %s", event_type, exc)
    except Exception:
        logger.exception("Unexpected failure recording product event %s", event_type)
