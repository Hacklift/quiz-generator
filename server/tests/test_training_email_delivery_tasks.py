from datetime import datetime, timezone

from bson import ObjectId

import server.app.quiz.tasks.training_email_delivery_tasks as delivery_tasks
from server.app.email_platform.models import SendResult


class FakeDeliveryCollection:
    def __init__(self, document):
        self.document = document

    def find_one_and_update(self, query, update, return_document):
        if self.document["_id"] != query["_id"] or self.document["status"] != query["status"]:
            return None
        if query.get("lease_token") != self.document.get("lease_token"):
            return None
        self.document.update(update["$set"])
        return dict(self.document)

    def update_one(self, query, update):
        if self.document["_id"] != query["_id"] or self.document["status"] != query["status"]:
            return None
        if query.get("lease_token") != self.document.get("lease_token"):
            return None
        self.document.update(update["$set"])
        return None


class FakeDatabase:
    def __init__(self, deliveries):
        self.deliveries = deliveries

    def __getitem__(self, name):
        assert name == delivery_tasks.OUTBOX_COLLECTION
        return self.deliveries


class FakeMongoClient:
    def __init__(self, deliveries):
        self.database = FakeDatabase(deliveries)
        self.closed = False

    def __getitem__(self, name):
        return self.database

    def close(self):
        self.closed = True


def _delivery_document():
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(),
        "recipient_email": "learner@example.com",
        "template_id": "custom",
        "template_vars": {"subject": "Training assigned", "body": "Complete it."},
        "status": "queued",
        "lease_token": "lease-1",
        "attempt_count": 0,
        "lease_expires_at": now,
        "updated_at": now,
    }


def _task_run(task):
    return getattr(task, "_orig_run", task.run)


def test_delivery_worker_marks_claimed_delivery_sent(monkeypatch):
    collection = FakeDeliveryCollection(_delivery_document())
    client = FakeMongoClient(collection)

    class SuccessfulWorkerEmailService:
        async def send_worker_email(self, **kwargs):
            assert kwargs["to"] == "learner@example.com"
            assert kwargs["purpose"] == "training_invitation"
            return SendResult(ok=True, adapter="mailgun")

    monkeypatch.setattr(delivery_tasks, "MongoClient", lambda uri: client)
    monkeypatch.setattr(
        delivery_tasks,
        "build_worker_email_service",
        SuccessfulWorkerEmailService,
    )

    delivered = _task_run(delivery_tasks.deliver_training_invitation)(
        str(collection.document["_id"]), collection.document["lease_token"]
    )

    assert delivered is True
    assert collection.document["status"] == "sent"
    assert collection.document["provider"] == "mailgun"
    assert collection.document["sent_at"] is not None
    assert client.closed is True


def test_delivery_worker_records_retry_after_provider_failure(monkeypatch):
    collection = FakeDeliveryCollection(_delivery_document())
    client = FakeMongoClient(collection)

    class FailingWorkerEmailService:
        async def send_worker_email(self, **kwargs):
            raise RuntimeError("Mailgun unavailable")

    monkeypatch.setattr(delivery_tasks, "MongoClient", lambda uri: client)
    monkeypatch.setattr(
        delivery_tasks,
        "build_worker_email_service",
        FailingWorkerEmailService,
    )

    delivered = _task_run(delivery_tasks.deliver_training_invitation)(
        str(collection.document["_id"]), collection.document["lease_token"]
    )

    assert delivered is False
    assert collection.document["status"] == "retry"
    assert collection.document["attempt_count"] == 1
    assert collection.document["next_attempt_at"] is not None
    assert "Mailgun unavailable" in collection.document["last_error"]


def test_stale_delivery_task_cannot_claim_a_newer_lease(monkeypatch):
    collection = FakeDeliveryCollection(_delivery_document())
    client = FakeMongoClient(collection)
    monkeypatch.setattr(delivery_tasks, "MongoClient", lambda uri: client)

    delivered = _task_run(delivery_tasks.deliver_training_invitation)(
        str(collection.document["_id"]), "stale-lease"
    )

    assert delivered is False
    assert collection.document["status"] == "queued"
