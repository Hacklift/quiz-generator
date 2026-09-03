import os
from datetime import datetime, timezone

from pymongo import MongoClient, ReturnDocument

from server.celery_config import celery_app


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


@celery_app.task(name="tasks.close_expired_training_runs")
def close_expired_training_runs() -> int:
    """Close due runs and persist their final audit snapshot exactly once."""
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    try:
        database = client[os.getenv("DB_NAME", "quizApp_db")]
        runs = database["training_runs"]
        assignments = database["training_assignments"]
        sessions = database["live_quiz_sessions"]
        audit_events = database["training_audit_events"]
        now = _utc_now()
        closed_count = 0

        for run in runs.find({"status": "open", "closes_at": {"$lte": now}}):
            closed = runs.find_one_and_update(
                {"_id": run["_id"], "status": "open"},
                {"$set": {"status": "closed", "closed_at": now, "updated_at": now}},
                return_document=ReturnDocument.AFTER,
            )
            if not closed:
                continue

            run_id = str(closed["_id"])
            assignment_rows = list(assignments.find({"training_run_id": run_id}))
            session_rows = list(sessions.find({"training_run_id": run_id}))
            audit_events.insert_one(
                {
                    "training_run_id": run_id,
                    "event_type": "run_closed",
                    "actor_user_id": None,
                    "occurred_at": now,
                    "payload": {
                        "run": {
                            "quiz_id": closed["quiz_id"],
                            "title": closed["title"],
                            "kind": closed["kind"],
                            "purpose": closed["purpose"],
                            "quiz_content_fingerprint": closed.get("quiz_content_fingerprint"),
                            "quiz_snapshot": closed.get("quiz_snapshot"),
                            "closes_at": closed["closes_at"],
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
            )
            closed_count += 1

        return closed_count
    finally:
        client.close()
