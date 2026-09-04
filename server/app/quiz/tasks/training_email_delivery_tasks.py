"""Durable provider-fallback delivery for training invitations.

The HTTP request only persists outbox records. These tasks provide at-least-once
delivery with a lease so broker or worker failures cannot strand invitations.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timedelta, timezone
import logging
import os
import uuid

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, ReturnDocument

from server.celery_config import celery_app
from server.app.email_platform.service import build_worker_email_service


logger = logging.getLogger(__name__)
OUTBOX_COLLECTION = "training_email_deliveries"
DISPATCH_BATCH_SIZE = 250
DELIVERY_LEASE = timedelta(minutes=10)
DELIVERY_HEARTBEAT_SECONDS = 60
MAX_DELIVERY_ATTEMPTS = 5


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _database(client: MongoClient):
    return client[os.getenv("DB_NAME", "quizApp_db")]


def _due_delivery_query(now: datetime) -> dict:
    return {
        "$or": [
            {
                "status": {"$in": ["pending", "retry"]},
                "next_attempt_at": {"$lte": now},
            },
            {
                "status": {"$in": ["queued", "sending"]},
                "lease_expires_at": {"$lte": now},
            },
        ]
    }


def _schedule_retry(
    deliveries, delivery: dict, error: Exception, now: datetime, lease_token: str
) -> None:
    attempt_count = int(delivery.get("attempt_count", 0)) + 1
    terminal = attempt_count >= MAX_DELIVERY_ATTEMPTS
    delay_seconds = min(60 * (2 ** max(attempt_count - 1, 0)), 3600)
    deliveries.update_one(
        {
            "_id": delivery["_id"],
            "status": "sending",
            "lease_token": lease_token,
        },
        {
            "$set": {
                "status": "failed" if terminal else "retry",
                "attempt_count": attempt_count,
                "next_attempt_at": None if terminal else now + timedelta(seconds=delay_seconds),
                "lease_expires_at": None,
                "last_error": str(error)[:500],
                "updated_at": now,
            }
        },
    )


def _renew_delivery_lease(deliveries, delivery_id: ObjectId, lease_token: str) -> bool:
    """Extend a lease only while this worker still owns the delivery."""
    now = _utc_now()
    result = deliveries.update_one(
        {
            "_id": delivery_id,
            "status": "sending",
            "lease_token": lease_token,
        },
        {
            "$set": {
                "lease_expires_at": now + DELIVERY_LEASE,
                "updated_at": now,
            }
        },
    )
    return bool(getattr(result, "matched_count", 0))


def _send_delivery_with_lease_heartbeat(
    deliveries, delivery: dict, lease_token: str
):
    """Deliver without allowing a healthy slow provider call to lose its lease.

    Provider adapters perform blocking network I/O. Running that call in a
    dedicated thread lets this worker renew the durable Mongo lease without
    introducing a Redis polling loop or a second delivery worker.
    """
    def send():
        return asyncio.run(
            build_worker_email_service().send_worker_email(
                to=delivery["recipient_email"],
                template_id=delivery["template_id"],
                template_vars=delivery["template_vars"],
                purpose=delivery.get("purpose", "training_invitation"),
            )
        )

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="training-email") as executor:
        future = executor.submit(send)
        while True:
            try:
                return future.result(timeout=DELIVERY_HEARTBEAT_SECONDS)
            except FutureTimeoutError:
                if not _renew_delivery_lease(
                    deliveries, delivery["_id"], lease_token
                ):
                    # Do not write a terminal state after losing ownership.
                    # The original provider call must still finish before this
                    # task exits, but another worker now owns reconciliation.
                    logger.warning(
                        "Training invitation delivery %s lost its lease while sending",
                        delivery["_id"],
                    )


@celery_app.task(name="tasks.dispatch_training_invitation_deliveries", ignore_result=True)
def dispatch_training_invitation_deliveries() -> int:
    """Queue a bounded number of due outbox records for independent delivery."""
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    try:
        deliveries = _database(client)[OUTBOX_COLLECTION]
        now = _utc_now()
        dispatched = 0
        candidates = deliveries.find(_due_delivery_query(now)).sort(
            "created_at", 1
        ).limit(DISPATCH_BATCH_SIZE)
        for candidate in candidates:
            lease_token = str(uuid.uuid4())
            queued = deliveries.find_one_and_update(
                {"_id": candidate["_id"], **_due_delivery_query(now)},
                {
                    "$set": {
                        "status": "queued",
                        "lease_token": lease_token,
                        "lease_expires_at": now + DELIVERY_LEASE,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if not queued:
                continue
            try:
                celery_app.send_task(
                    "tasks.deliver_training_invitation",
                    args=[str(queued["_id"]), lease_token],
                    queue="email",
                    ignore_result=True,
                )
                dispatched += 1
            except Exception as error:
                # Keep it durable for the next dispatcher invocation.
                deliveries.update_one(
                    {"_id": queued["_id"], "status": "queued", "lease_token": lease_token},
                    {
                        "$set": {
                            "status": "retry",
                            "next_attempt_at": now + timedelta(minutes=1),
                            "lease_expires_at": None,
                            "last_error": str(error)[:500],
                            "updated_at": now,
                        }
                    },
                )
                logger.exception(
                    "Could not queue training invitation delivery %s", queued["_id"]
                )
        return dispatched
    finally:
        client.close()


@celery_app.task(name="tasks.deliver_training_invitation", ignore_result=True)
def deliver_training_invitation(delivery_id: str, lease_token: str) -> bool:
    """Claim one queued record and deliver it through worker-safe providers."""
    try:
        object_id = ObjectId(delivery_id)
    except (InvalidId, TypeError):
        logger.error("Invalid training invitation delivery id: %s", delivery_id)
        return False

    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    try:
        deliveries = _database(client)[OUTBOX_COLLECTION]
        now = _utc_now()
        delivery = deliveries.find_one_and_update(
            {"_id": object_id, "status": "queued", "lease_token": lease_token},
            {
                "$set": {
                    "status": "sending",
                    "lease_expires_at": now + DELIVERY_LEASE,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not delivery:
            return False

        try:
            result = _send_delivery_with_lease_heartbeat(
                deliveries, delivery, lease_token
            )
            deliveries.update_one(
                {
                    "_id": object_id,
                    "status": "sending",
                    "lease_token": lease_token,
                },
                {
                    "$set": {
                        "status": "sent",
                        "provider": result.adapter,
                        "provider_message_id": result.provider_message_id,
                        "sent_at": _utc_now(),
                        "lease_expires_at": None,
                        "last_error": None,
                        "updated_at": _utc_now(),
                    }
                },
            )
            return True
        except Exception as error:
            _schedule_retry(deliveries, delivery, error, _utc_now(), lease_token)
            logger.exception("Training invitation delivery failed: %s", delivery_id)
            return False
    finally:
        client.close()
