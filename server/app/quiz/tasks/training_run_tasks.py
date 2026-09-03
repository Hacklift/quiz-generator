import os
import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, ReturnDocument

from server.celery_config import celery_app
from server.app.quiz.utils.session_grading import grade_live_session


logger = logging.getLogger(__name__)
ACTIVE_SESSION_STATUSES = ["active", "joined", "disconnected"]
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
    return {
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": "training",
        "action_url": action_url,
        "expires_at": None,
        "dedupe_key": dedupe_key,
        "read": False,
        "created_at": now,
    }


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
            "status": {"$in": ACTIVE_SESSION_STATUSES},
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


@celery_app.task(name="tasks.close_expired_training_runs")
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
            "closes_at": {"$lte": now},
            "$or": [
                {"closure_in_progress": {"$ne": True}},
                {"closure_started_at": {"$lte": now - LOCK_STALE_AFTER}},
            ],
        }
        for candidate in runs.find(due_query):
            run = runs.find_one_and_update(
                {"_id": candidate["_id"], **due_query},
                {
                    "$set": {
                        "closure_in_progress": True,
                        "closure_started_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if not run:
                continue
            run_id = str(run["_id"])
            try:
                expiring_sessions = sessions.find(
                    {
                        "training_run_id": run_id,
                        "status": {"$in": ACTIVE_SESSION_STATUSES},
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

                assignment_rows = list(assignments.find({"training_run_id": run_id}))
                session_rows = list(sessions.find({"training_run_id": run_id}))
                audit_events.update_one(
                    {"training_run_id": run_id, "event_type": "run_closed"},
                    {
                        "$setOnInsert": {
                            "training_run_id": run_id,
                            "event_type": "run_closed",
                            "actor_user_id": None,
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
                        },
                    },
                    return_document=ReturnDocument.AFTER,
                )
                if closed:
                    closed_count += 1
            except Exception:
                logger.exception("Could not close training run %s", run_id)
                runs.update_one(
                    {"_id": run["_id"], "status": "open"},
                    {"$unset": {"closure_in_progress": "", "closure_started_at": ""}},
                )

        return closed_count
    finally:
        client.close()
