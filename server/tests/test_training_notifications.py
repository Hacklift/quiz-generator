from datetime import datetime
from unittest.mock import AsyncMock

import pytest

import server.app.quiz.services.training_notification_service as notification_module
from server.app.quiz.services.training_notification_service import TrainingNotificationService


class FakeRunsCollection:
    async def find_one(self, query):
        assert query
        return {"title": "Security basics", "owner_user_id": "owner-1"}


@pytest.mark.asyncio
async def test_assignment_notification_is_actionable_and_idempotent(monkeypatch):
    create_notification = AsyncMock()
    monkeypatch.setattr(notification_module, "create_notification", create_notification)
    service = TrainingNotificationService(None, object(), FakeRunsCollection())

    await service.notify_assignment(
        {"_id": "assignment-1"},
        {"title": "Security basics", "closes_at": datetime(2026, 9, 10)},
        "user-1",
    )

    notification = create_notification.await_args.args[1]
    assert notification.action_url == "/assigned-training"
    assert notification.dedupe_key == "training-assignment:assignment-1:assigned"


@pytest.mark.asyncio
async def test_completion_notification_includes_the_assignment_score(monkeypatch):
    create_notification = AsyncMock()
    monkeypatch.setattr(notification_module, "create_notification", create_notification)
    service = TrainingNotificationService(None, object(), FakeRunsCollection())

    await service.notify_completion(
        {
            "_id": "assignment-1",
            "recipient_user_id": "user-1",
            "training_run_id": "64c13ab08edf48a008793cac",
            "latest_percentage": 80,
        }
    )

    notification = create_notification.await_args.args[1]
    assert notification.title == "Training completed"
    assert "80%" in notification.message
    assert notification.dedupe_key == "training-assignment:assignment-1:completed"


@pytest.mark.asyncio
async def test_owner_is_notified_for_shareable_link_completion(monkeypatch):
    create_notification = AsyncMock()
    monkeypatch.setattr(notification_module, "create_notification", create_notification)
    service = TrainingNotificationService(None, object(), FakeRunsCollection())

    await service.notify_run_owner_of_completion(
        {
            "_id": "session-1",
            "training_run_id": "64c13ab08edf48a008793cac",
            "participant_name": "Ada Lovelace",
            "percentage": 90,
        }
    )

    notification = create_notification.await_args.args[1]
    assert notification.user_id == "owner-1"
    assert notification.action_url == "/training-runs/64c13ab08edf48a008793cac"
    assert "Ada Lovelace" in notification.message
    assert "90%" in notification.message
    assert notification.dedupe_key == (
        "training-run:64c13ab08edf48a008793cac:session:session-1:owner-completed"
    )
