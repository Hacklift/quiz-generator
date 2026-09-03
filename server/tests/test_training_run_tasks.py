from datetime import datetime, timezone

from server.app.quiz.tasks.training_run_tasks import _finalize_expired_session


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
