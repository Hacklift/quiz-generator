from types import SimpleNamespace

import pytest

from server.app.db.core.connection import ensure_notification_indexes
from server.app.notifications.repository import create_notification
from server.app.notifications.schemas import NotificationCreate


class FakeNotificationsCollection:
    def __init__(self):
        self.documents = []
        self.dropped_indexes = []
        self.created_indexes = []

    async def insert_one(self, document):
        document = {**document, "_id": f"notification-{len(self.documents) + 1}"}
        self.documents.append(document)
        return SimpleNamespace(inserted_id=document["_id"])

    async def find_one(self, query):
        return next(
            (
                document
                for document in self.documents
                if all(document.get(key) == value for key, value in query.items())
            ),
            None,
        )

    async def index_information(self):
        return {
            "_id_": {"key": [("_id", 1)]},
            "notification_dedupe_key": {
                "key": [("dedupe_key", 1)],
                "unique": True,
                "sparse": True,
            },
        }

    async def create_index(self, keys, **kwargs):
        self.created_indexes.append((keys, kwargs))

    async def drop_index(self, index_name):
        self.dropped_indexes.append(index_name)


@pytest.mark.asyncio
async def test_notification_without_dedupe_key_omits_the_field():
    collection = FakeNotificationsCollection()

    await create_notification(
        collection,
        NotificationCreate(
            user_id="user-1",
            title="System notice",
            message="No dedupe key is required for this notification.",
        ),
    )

    assert "dedupe_key" not in collection.documents[0]


@pytest.mark.asyncio
async def test_notification_index_migrates_sparse_unique_to_partial_unique():
    collection = FakeNotificationsCollection()

    await ensure_notification_indexes(collection)

    assert collection.dropped_indexes == ["notification_dedupe_key"]
    _, options = collection.created_indexes[-1]
    assert options["name"] == "notification_dedupe_key"
    assert options["unique"] is True
    assert options["partialFilterExpression"] == {"dedupe_key": {"$type": "string"}}
