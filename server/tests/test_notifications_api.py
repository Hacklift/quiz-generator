from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from server.app.notifications.schemas import (
    AdminNotificationCreate,
    BroadcastNotificationCreate,
    NotificationResponse,
    NotificationType,
)
from server.app.notifications.services import (
    broadcast_admin_notification,
    create_admin_notification,
    delete_user_notification,
    get_notifications_for_user,
    get_unread_count_for_user,
    mark_user_notification_read,
)
from server.app.users.models import UserOut


def _user(role: str = "user") -> UserOut:
    return UserOut(
        id=str(ObjectId()),
        username=f"{role}-user",
        email=f"{role}@example.com",
        role=role,
        is_active=True,
        is_verified=True,
    )


def _notification(user_id: str) -> NotificationResponse:
    return NotificationResponse(
        id=str(ObjectId()),
        user_id=user_id,
        title="System update",
        message="A notification message",
        type=NotificationType.SYSTEM,
        read=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_notifications_for_user_returns_notifications_and_unread_count():
    current_user = _user()
    notification = _notification(current_user.id)
    notifications_collection = MagicMock()

    with patch(
        "server.app.notifications.services.list_user_notifications",
        new=AsyncMock(return_value=([notification], False)),
    ) as list_mock, patch(
        "server.app.notifications.services.count_unread_notifications",
        new=AsyncMock(return_value=1),
    ) as count_mock:
        result = await get_notifications_for_user(
            notifications_collection=notifications_collection,
            user=current_user,
            limit=20,
            skip=0,
        )

    assert result.notifications == [notification]
    assert result.unread_count == 1
    assert result.has_more is False
    list_mock.assert_awaited_once_with(
        notifications_collection=notifications_collection,
        user_id=current_user.id,
        limit=20,
        skip=0,
    )
    count_mock.assert_awaited_once_with(notifications_collection, current_user.id)


@pytest.mark.asyncio
async def test_get_unread_count_for_user_returns_count_only():
    current_user = _user()
    notifications_collection = MagicMock()

    with patch(
        "server.app.notifications.services.count_unread_notifications",
        new=AsyncMock(return_value=3),
    ) as count_mock:
        result = await get_unread_count_for_user(
            notifications_collection=notifications_collection,
            user=current_user,
        )

    assert result.unread_count == 3
    count_mock.assert_awaited_once_with(notifications_collection, current_user.id)


@pytest.mark.asyncio
async def test_non_admin_cannot_create_notification_for_user():
    payload = AdminNotificationCreate(
        user_id=str(ObjectId()),
        title="Admin notice",
        message="Only admins can create this.",
    )

    with pytest.raises(HTTPException) as exc:
        await create_admin_notification(
            notifications_collection=MagicMock(),
            users_collection=MagicMock(),
            payload=payload,
            user=_user(role="user"),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_admin_create_notification_validates_target_user_exists():
    target_user_id = ObjectId()
    payload = AdminNotificationCreate(
        user_id=str(target_user_id),
        title="Admin notice",
        message="Targeted account notification.",
        type=NotificationType.ADMIN,
    )
    users_collection = MagicMock()
    users_collection.find_one = AsyncMock(return_value={"_id": target_user_id})
    notifications_collection = MagicMock()
    expected = _notification(str(target_user_id))

    with patch(
        "server.app.notifications.services.create_notification",
        new=AsyncMock(return_value=expected),
    ) as create_mock:
        result = await create_admin_notification(
            notifications_collection=notifications_collection,
            users_collection=users_collection,
            payload=payload,
            user=_user(role="admin"),
        )

    assert result == expected
    users_collection.find_one.assert_awaited_once_with({"_id": target_user_id})
    create_mock.assert_awaited_once_with(notifications_collection, payload)


@pytest.mark.asyncio
async def test_admin_create_notification_rejects_missing_target_user():
    payload = AdminNotificationCreate(
        user_id=str(ObjectId()),
        title="Admin notice",
        message="Targeted account notification.",
    )
    users_collection = MagicMock()
    users_collection.find_one = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await create_admin_notification(
            notifications_collection=MagicMock(),
            users_collection=users_collection,
            payload=payload,
            user=_user(role="admin"),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_admin_broadcast_notification_targets_active_users_by_default():
    user_ids = [ObjectId(), ObjectId()]
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"_id": user_id} for user_id in user_ids])
    users_collection = MagicMock()
    users_collection.find.return_value = cursor
    notifications_collection = MagicMock()
    payload = BroadcastNotificationCreate(
        title="Maintenance",
        message="A scheduled maintenance message.",
    )

    with patch(
        "server.app.notifications.services.create_notifications_for_users",
        new=AsyncMock(return_value=2),
    ) as create_many_mock:
        result = await broadcast_admin_notification(
            notifications_collection=notifications_collection,
            users_collection=users_collection,
            payload=payload,
            user=_user(role="admin"),
        )

    assert result.created_count == 2
    assert result.message == "Broadcast notification created"
    users_collection.find.assert_called_once_with(
        {"is_active": True},
        projection={"_id": 1},
    )
    create_many_mock.assert_awaited_once()
    _, kwargs = create_many_mock.await_args
    assert kwargs["notifications_collection"] is notifications_collection
    assert kwargs["user_ids"] == [str(user_id) for user_id in user_ids]
    assert kwargs["notification"].title == payload.title
    assert kwargs["notification"].message == payload.message


@pytest.mark.asyncio
async def test_mark_notification_read_returns_404_when_not_owned_or_missing():
    with patch(
        "server.app.notifications.services.mark_notification_read",
        new=AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            await mark_user_notification_read(
                notifications_collection=MagicMock(),
                notification_id=str(ObjectId()),
                user=_user(),
            )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Notification not found"


@pytest.mark.asyncio
async def test_delete_notification_returns_404_when_not_owned_or_missing():
    with patch(
        "server.app.notifications.services.delete_notification",
        new=AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            await delete_user_notification(
                notifications_collection=MagicMock(),
                notification_id=str(ObjectId()),
                user=_user(),
            )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Notification not found"
