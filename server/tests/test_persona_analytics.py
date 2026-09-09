from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.app.analytics.product_events import QUIZ_GENERATED, record_product_event
from server.app.analytics.reporting import aggregate_persona_events
from server.app.users.persona import analytics_persona_snapshot
from server.app.users.repository import record_auth_event


@pytest.mark.parametrize(
    "user",
    [
        None,
        {},
        {"profile": {}},
        {"profile": {"persona": {"category": "school"}}},
        {"profile": {"persona": {"category": "school", "user_type": "business"}}},
        {"profile": {"persona": {"category": "invalid", "user_type": "teacher"}}},
    ],
)
def test_analytics_persona_snapshot_collapses_invalid_or_partial_values(user):
    assert analytics_persona_snapshot(user) == {
        "persona_category": "unset",
        "persona_user_type": "unset",
    }


def test_analytics_persona_snapshot_uses_canonical_profile_pair():
    user = {
        "profile": {
            "persona": {
                "category": "school",
                "user_type": "teacher",
                "source": "profile",
            }
        }
    }
    assert analytics_persona_snapshot(user) == {
        "persona_category": "school",
        "persona_user_type": "teacher",
    }


@pytest.mark.asyncio
async def test_product_event_is_minimal_and_snapshots_persona_at_event_time():
    collection = SimpleNamespace(insert_one=AsyncMock())
    user = SimpleNamespace(persona_category="school", persona_user_type="teacher")

    await record_product_event(
        collection,
        event_type=QUIZ_GENERATED,
        user_id="user-1",
        user=user,
        quiz_id="quiz-1",
    )
    saved = collection.insert_one.await_args.args[0]
    user.persona_category = "corporate"
    user.persona_user_type = "business"

    assert saved["persona_category"] == "school"
    assert saved["persona_user_type"] == "teacher"
    assert set(saved) == {
        "event_type",
        "user_id",
        "persona_category",
        "persona_user_type",
        "quiz_id",
        "created_at",
    }


@pytest.mark.asyncio
async def test_auth_event_merges_persona_without_adding_profile_pii():
    collection = SimpleNamespace(insert_one=AsyncMock())
    user = {
        "email": "not-copied@example.test",
        "full_name": "Not Copied",
        "profile": {"persona": {"category": "corporate", "user_type": "hr"}},
    }

    await record_auth_event(
        collection,
        event_type="login_success",
        status="success",
        user_id="user-1",
        metadata={"session_id": "session-1"},
        user=user,
    )
    saved = collection.insert_one.await_args.args[0]

    assert saved["metadata"] == {
        "session_id": "session-1",
        "persona": {"category": "corporate", "user_type": "hr"},
    }
    assert "email" not in saved and "full_name" not in saved


def test_report_groups_signup_and_generation_and_normalizes_legacy_events():
    timestamp = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
    auth_events = [
        {
            "created_at": timestamp,
            "metadata": {"persona": {"category": "school", "user_type": "parent"}},
        },
        {"created_at": timestamp, "metadata": {}},
    ]
    product_events = [
        {
            "created_at": timestamp,
            "persona_category": "school",
            "persona_user_type": "parent",
        },
        {"created_at": timestamp, "persona_category": "school"},
    ]

    assert aggregate_persona_events(auth_events, product_events, "month") == [
        {
            "period": "2026-09",
            "persona_category": "school",
            "persona_user_type": "parent",
            "signups": 1,
            "generations": 1,
        },
        {
            "period": "2026-09",
            "persona_category": "unset",
            "persona_user_type": "unset",
            "signups": 1,
            "generations": 1,
        },
    ]
