"""Canonical persistence shape for notification documents."""

from .schemas import NotificationCreate, NotificationDB


def build_notification_document(notification: NotificationCreate) -> dict:
    """Exclude optional fields so partial indexes retain their intended semantics."""
    return NotificationDB(**notification.model_dump()).model_dump(exclude_none=True)
