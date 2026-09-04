from datetime import datetime, timezone

from bson import ObjectId

import server.app.quiz.tasks.training_run_tasks as training_tasks
from server.app.quiz.tasks.training_run_tasks import (
    _finalize_expired_session,
    _reconcile_submitted_assignment_sessions,
)


class FakeSessions:
    def __init__(self, session):
        self.session = session

    def find_one_and_update(self, query, update, **_kwargs):
        if self.session["status"] not in query["status"]["$in"]:
            return None
        self.session.update(update["$set"])
        return self.session


class FakeNotifications:
    def __init__(self):
        self.documents = []

    def update_one(self, _query, update, **_kwargs):
        self.documents.append(update["$setOnInsert"])


class FakeRecoveryRuns:
    def __init__(self, run):
        self.run = run

    def find(self, _query):
        return [self.run]

    def find_one_and_update(self, _query, update, **_kwargs):
        if "$unset" in update:
            self.run.update(update["$set"])
            for field in update["$unset"]:
                self.run.pop(field, None)
            return self.run
        self.run.update(update["$set"])
        return self.run


class FakeRecoveryAssignments:
    def __init__(self, rows):
        self.rows = rows

    def update_many(self, _query, update):
        for row in self.rows:
            if row["status"] == "in_progress":
                row.update(update["$set"])

    def find(self, _query):
        return self.rows

    def update_one(self, query, update):
        for row in self.rows:
            if row["_id"] == query["_id"] and row["status"] == query["status"]:
                row.update(update["$set"])
                return


class FakeRecoverySessions:
    def __init__(self, rows):
        self.rows = rows

    def update_many(self, _query, update):
        for row in self.rows:
            if row["status"] in training_tasks.ACTIVE_SESSION_STATUSES:
                row.update(update["$set"])

    def find(self, _query):
        return self.rows


class FakeAuditEvents:
    def __init__(self):
        self.documents = []

    def update_one(self, _query, update, **_kwargs):
        self.documents.append(update["$setOnInsert"])


class FakeDatabase:
    def __init__(self, run, assignments, sessions):
        self.runs = FakeRecoveryRuns(run)
        self.assignments = FakeRecoveryAssignments(assignments)
        self.sessions = FakeRecoverySessions(sessions)
        self.audit_events = FakeAuditEvents()
        self.notifications = FakeNotifications()

    def __getitem__(self, name):
        return {
            "training_runs": self.runs,
            "training_assignments": self.assignments,
            "live_quiz_sessions": self.sessions,
            "training_audit_events": self.audit_events,
            "notifications": self.notifications,
        }[name]


class FakeClient:
    def __init__(self, database):
        self.database = database
        self.closed = False

    def __getitem__(self, _name):
        return self.database

    def close(self):
        self.closed = True


def test_closure_worker_finalizes_an_expired_shared_session_from_its_snapshot():
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    session = {
        "_id": "session-1",
        "training_run_id": "run-1",
        "status": "joined",
        "started_at": datetime(2026, 9, 3, 11, 59),
        "expires_at": datetime(2026, 9, 3, 12, 0),
        "participant_name": "Ada",
        "answers": [{"question_index": 0, "selected_answer": "A"}],
    }
    run = {
        "_id": "run-1",
        "owner_user_id": "owner-1",
        "title": "Security basics",
        "quiz_snapshot": {
            "quiz_type": "multichoice",
            "questions": [{"question": "Q", "answer": "A", "options": ["A", "B"]}],
        },
    }
    sessions = FakeSessions(session)
    notifications = FakeNotifications()

    _finalize_expired_session(
        session=session,
        run=run,
        assignments=None,
        sessions=sessions,
        notifications=notifications,
        now=now,
    )

    assert sessions.session["status"] == "submitted"
    assert sessions.session["score"] == 1
    assert notifications.documents[0]["user_id"] == "owner-1"


def test_closure_worker_recovers_a_stale_manual_close_without_reopening_the_run(monkeypatch):
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    run = {
        "_id": "run-1",
        "quiz_id": "quiz-1",
        "owner_user_id": "owner-1",
        "title": "Safety training",
        "kind": "compliance",
        "purpose": "health_and_safety",
        "closes_at": now + training_tasks.LOCK_STALE_AFTER,
        "status": "open",
        "closure_in_progress": True,
        "closure_started_at": now - training_tasks.LOCK_STALE_AFTER,
        "closure_mode": "manual",
        "closure_actor_user_id": "owner-1",
    }
    assignments = [{"_id": "assignment-1", "recipient_email": "learner@example.com", "status": "in_progress"}]
    sessions = [{"_id": "session-1", "training_run_id": "run-1", "status": "active"}]
    database = FakeDatabase(run, assignments, sessions)
    client = FakeClient(database)
    monkeypatch.setattr(training_tasks, "MongoClient", lambda _uri: client)
    monkeypatch.setattr(training_tasks, "_utc_now", lambda: now)

    closed_count = training_tasks.close_expired_training_runs()

    assert closed_count == 1
    assert run["status"] == "closed"
    assert "closure_in_progress" not in run
    assert assignments[0]["status"] == "incomplete"
    assert sessions[0]["status"] == "abandoned"
    assert database.audit_events.documents[0]["payload"]["completion_register"][0]["status"] == "incomplete"
    assert database.audit_events.documents[0]["actor_user_id"] == "owner-1"
    assert client.closed is True


def test_closure_worker_reconciles_a_submission_that_won_the_boundary_race():
    assignment_id = ObjectId()
    submitted_at = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    assignments = FakeRecoveryAssignments(
        [
            {
                "_id": assignment_id,
                "training_run_id": "run-1",
                "status": "in_progress",
            }
        ]
    )
    sessions = FakeRecoverySessions(
        [
            {
                "_id": "session-1",
                "training_run_id": "run-1",
                "training_assignment_id": str(assignment_id),
                "status": "submitted",
                "submitted_at": submitted_at,
                "score": 8,
                "percentage": 80,
            }
        ]
    )

    _reconcile_submitted_assignment_sessions(
        assignments, sessions, "run-1", submitted_at
    )

    assert assignments.rows[0]["status"] == "completed"
    assert assignments.rows[0]["latest_session_id"] == "session-1"
    assert assignments.rows[0]["latest_percentage"] == 80
