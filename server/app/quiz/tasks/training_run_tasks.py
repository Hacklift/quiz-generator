import os
import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, ReturnDocument

from server.celery_config import celery_app
from server.app.notifications.documents import build_notification_document
from server.app.notifications.schemas import NotificationCreate, NotificationType
from server.app.quiz.utils.session_grading import grade_live_session


logger = logging.getLogger(__name__)
ACTIVE_SESSION_STATUSES = ["active", "joined", "disconnected"]
CLOSING_SESSION_STATUS = "closing"
LOCK_STALE_AFTER = timedelta(minutes=15)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _assignment_snapshot(assignment: dict) -> dict:
    return {
        "assignment_id": str(assignment["_id"]),
        "recipient_email": assignment["recipient_email"],
        "status": assignment["status"],
        "attempts_used": assignment.get("attempts_used", 0),
        "max_attempts": assignment.get("max_attempts"),
        "started_at": assignment.get("started_at"),
        "completed_at": assignment.get("completed_at"),
        "latest_score": assignment.get("latest_score"),
        "latest_percentage": assignment.get("latest_percentage"),
    }


def _shared_session_snapshot(session: dict) -> dict:
    return {
        "session_id": str(session["_id"]),
        "participant_name": session.get("participant_name"),
        "participant_email": session.get("participant_email"),
        "status": session.get("status"),
        "started_at": session.get("started_at"),
        "submitted_at": session.get("submitted_at"),
        "score": session.get("score"),
        "percentage": session.get("percentage"),
    }


def _notification_document(
    *,
    user_id: str,
    title: str,
    message: str,
    action_url: str,
    dedupe_key: str,
    now: datetime,
) -> dict:
    document = build_notification_document(
        NotificationCreate(
            user_id=user_id,
            title=title,
            message=message,
            type=NotificationType.TRAINING,
            action_url=action_url,
            dedupe_key=dedupe_key,
        )
    )
    document["created_at"] = now
    return document


def _upsert_notification(notifications, document: dict) -> None:
    notifications.update_one(
        {"dedupe_key": document["dedupe_key"]},
        {"$setOnInsert": document},
        upsert=True,
    )


def _finalize_expired_session(
    *,
    session: dict,
    run: dict,
    assignments,
    sessions,
    notifications,
    now: datetime,
) -> None:
    quiz = session.get("quiz_snapshot") or run.get("quiz_snapshot")
    if not quiz or not quiz.get("questions"):
        logger.error(
            "Cannot finalize training session %s: quiz snapshot is unavailable",
            session["_id"],
        )
        return

    graded = grade_live_session(session, quiz)
    duration_used_seconds = max(
        0,
        int((now - _as_utc(session["started_at"])).total_seconds()),
    )
    updated = sessions.find_one_and_update(
        {
            "_id": session["_id"],
            "status": {"$in": [*ACTIVE_SESSION_STATUSES, CLOSING_SESSION_STATUS]},
            "expires_at": {"$lte": now},
        },
        {
            "$set": {
                "status": "submitted",
                "submitted_at": now,
                "score": graded["score"],
                "percentage": graded["percentage"],
                "graded_answers": graded["graded_answers"],
                "duration_used_seconds": duration_used_seconds,
                "auto_submitted": True,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        return

    assignment = None
    assignment_id = updated.get("training_assignment_id")
    if assignment_id:
        try:
            assignment_object_id = ObjectId(assignment_id)
        except (InvalidId, TypeError):
            assignment_object_id = None
        if assignment_object_id:
            assignment = assignments.find_one_and_update(
                {"_id": assignment_object_id},
                {
                    "$set": {
                        "status": "completed",
                        "latest_session_id": str(updated["_id"]),
                        "latest_score": graded["score"],
                        "latest_percentage": graded["percentage"],
                        "completed_at": now,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        if assignment and assignment.get("recipient_user_id"):
            _upsert_notification(
                notifications,
                _notification_document(
                    user_id=assignment["recipient_user_id"],
                    title="Training completed",
                    message=(
                        f"You completed {run['title']}. "
                        f"Your score: {graded['percentage']}%."
                    ),
                    action_url="/assigned-training",
                    dedupe_key=f"training-assignment:{assignment['_id']}:completed",
                    now=now,
                ),
            )

    participant = (
        assignment.get("recipient_email")
        if assignment
        else updated.get("participant_name") or updated.get("participant_email")
    ) or "A participant"
    _upsert_notification(
        notifications,
        _notification_document(
            user_id=run["owner_user_id"],
            title="Training completed",
            message=(
                f"{participant} completed {run['title']}. "
                f"Score: {graded['percentage']}%."
            ),
            action_url=f"/training-runs/{run['_id']}",
            dedupe_key=(
                f"training-run:{run['_id']}:session:{updated['_id']}:owner-completed"
            ),
            now=now,
        ),
    )


def _reconcile_submitted_assignment_sessions(assignments, sessions, run_id: str, now: datetime) -> None:
    """Finish the tiny session/assignment write gap before sealing an audit snapshot.

    A participant can submit just before the closure worker claims the run. The
    live-session write is durable first, while its assignment summary follows
    immediately after. Reconcile only assignments still marked in progress so
    a prior completed attempt can never overwrite a later retry.
    """
    assignment_rows = list(
        assignments.find({"training_run_id": run_id, "status": "in_progress"})
    )
    submitted_by_assignment: dict[str, dict] = {}
    for session in sessions.find(
        {
            "training_run_id": run_id,
            "training_assignment_id": {"$exists": True},
            "status": "submitted",
        }
    ):
        assignment_id = session.get("training_assignment_id")
        if not assignment_id:
            continue
        previous = submitted_by_assignment.get(str(assignment_id))
        if not previous or _as_utc(session["submitted_at"]) > _as_utc(previous["submitted_at"]):
            submitted_by_assignment[str(assignment_id)] = session

    for assignment in assignment_rows:
        session = submitted_by_assignment.get(str(assignment["_id"]))
        if not session:
            continue
        assignments.update_one(
            {"_id": assignment["_id"], "status": "in_progress"},
            {
                "$set": {
                    "status": "completed",
                    "latest_session_id": str(session["_id"]),
                    "latest_score": session.get("score"),
                    "latest_percentage": session.get("percentage"),
                    "completed_at": session.get("submitted_at") or now,
                    "updated_at": now,
                }
            },
        )


@celery_app.task(name="tasks.close_expired_training_runs", ignore_result=True)
def close_expired_training_runs() -> int:
    """Finalize due sessions, then close each run with one final audit snapshot."""
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    try:
        database = client[os.getenv("DB_NAME", "quizApp_db")]
        runs = database["training_runs"]
        assignments = database["training_assignments"]
        sessions = database["live_quiz_sessions"]
        audit_events = database["training_audit_events"]
        notifications = database["notifications"]
        now = _utc_now()
        closed_count = 0

        due_query = {
            "status": "open",
            "$or": [
                {
                    "closes_at": {"$lte": now},
                    "closure_in_progress": {"$ne": True},
                },
                {
                    "closure_in_progress": True,
                    "closure_started_at": {"$lte": now - LOCK_STALE_AFTER},
                },
            ],
        }
        for candidate in runs.find(due_query):
            is_recovery = candidate.get("closure_in_progress") is True
            claim_query = {
                "_id": candidate["_id"],
                "status": "open",
                "closure_in_progress": True,
                "closure_started_at": {"$lte": now - LOCK_STALE_AFTER},
            } if is_recovery else {
                "_id": candidate["_id"],
                "status": "open",
                "closure_in_progress": {"$ne": True},
                "closes_at": {"$lte": now},
            }
            claim_update = {
                "$set": {"closure_started_at": now, "updated_at": now},
            }
            if not is_recovery:
                claim_update["$set"].update(
                    {
                        "closure_in_progress": True,
                        "closure_mode": "scheduled",
                        "closure_actor_user_id": None,
                    }
                )
            run = runs.find_one_and_update(
                claim_query,
                claim_update,
                return_document=ReturnDocument.AFTER,
            )
            if not run:
                continue
            run_id = str(run["_id"])
            try:
                if run.get("closure_mode") == "manual":
                    assignments.update_many(
                        {"training_run_id": run_id, "status": "in_progress"},
                        {"$set": {"status": "incomplete", "updated_at": now}},
                    )
                    sessions.update_many(
                        {
                            "training_run_id": run_id,
                            "status": {"$in": ACTIVE_SESSION_STATUSES},
                        },
                        {
                            "$set": {
                                "status": "abandoned",
                                "abandoned_at": now,
                                "updated_at": now,
                            }
                        },
                    )
                else:
                    # Claim expiring sessions before grading. A participant
                    # that started its submit just before this claim can still
                    # win, but the reconciliation below records that durable
                    # session before the immutable register is written.
                    sessions.update_many(
                        {
                            "training_run_id": run_id,
                            "status": {"$in": ACTIVE_SESSION_STATUSES},
                            "expires_at": {"$lte": now},
                        },
                        {
                            "$set": {
                                "status": CLOSING_SESSION_STATUS,
                                "updated_at": now,
                            }
                        },
                    )
                    expiring_sessions = sessions.find(
                        {
                            "training_run_id": run_id,
                            "status": CLOSING_SESSION_STATUS,
                            "expires_at": {"$lte": now},
                        }
                    )
                    for session in expiring_sessions:
                        _finalize_expired_session(
                            session=session,
                            run=run,
                            assignments=assignments,
                            sessions=sessions,
                            notifications=notifications,
                            now=now,
                        )

                    _reconcile_submitted_assignment_sessions(
                        assignments, sessions, run_id, now
                    )
                assignment_rows = list(assignments.find({"training_run_id": run_id}))
                session_rows = list(sessions.find({"training_run_id": run_id}))
                audit_events.update_one(
                    {"training_run_id": run_id, "event_type": "run_closed"},
                    {
                        "$setOnInsert": {
                            "training_run_id": run_id,
                            "event_type": "run_closed",
                            "actor_user_id": run.get("closure_actor_user_id"),
                            "occurred_at": now,
                            "payload": {
                                "run": {
                                    "quiz_id": run["quiz_id"],
                                    "title": run["title"],
                                    "kind": run["kind"],
                                    "purpose": run["purpose"],
                                    "quiz_content_fingerprint": run.get("quiz_content_fingerprint"),
                                    "quiz_snapshot": run.get("quiz_snapshot"),
                                    "closes_at": run["closes_at"],
                                },
                                "completion_register": [
                                    *[_assignment_snapshot(item) for item in assignment_rows],
                                    *[
                                        _shared_session_snapshot(item)
                                        for item in session_rows
                                        if not item.get("training_assignment_id")
                                    ],
                                ],
                            },
                        }
                    },
                    upsert=True,
                )
                closed = runs.find_one_and_update(
                    {
                        "_id": run["_id"],
                        "status": "open",
                        "closure_in_progress": True,
                    },
                    {
                        "$set": {
                            "status": "closed",
                            "closed_at": now,
                            "updated_at": now,
                        },
                        "$unset": {
                            "closure_in_progress": "",
                            "closure_started_at": "",
                            "closure_mode": "",
                            "closure_actor_user_id": "",
                        },
                    },
                    return_document=ReturnDocument.AFTER,
                )
                if closed:
                    closed_count += 1
            except Exception:
                logger.exception("Could not close training run %s", run_id)
                # Do not reopen a partially terminalized run. The next stale
                # recovery pass resumes from the same durable lock.

        return closed_count
    finally:
        client.close()
