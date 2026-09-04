import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

import server.app.quiz.services.live_session_service as live_session_module
import server.app.quiz.services.training_run_service as training_run_module
from server.app.quiz.schemas.training_runs import (
    CloseTrainingRunRequest,
    CreateTrainingRunRequest,
)
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.services.training_run_service import TrainingRunService


class FakeAssignmentRepository:
    def __init__(self, run):
        self.run = run

    async def get_run(self, run_id):
        return self.run if run_id == "run-1" else None


class FakeTrainingSessionRepository:
    def __init__(self, quiz):
        self.quiz = quiz
        self.session = None

    async def create_session(self, session_data):
        self.session = {**session_data, "_id": "session-1"}
        return "session-1"

    async def get_session(self, session_id):
        return self.session

    async def get_quiz_by_id(self, quiz_id):
        return self.quiz

    async def update_session(self, session_id, updates):
        self.session = {**self.session, **updates}
        return self.session

    async def finalize_session(self, session_id, updates):
        if self.session["status"] == "submitted":
            return None
        self.session = {**self.session, **updates}
        return self.session


class FailingRealtimeBroadcaster:
    async def publish(self, _quiz_id, _event):
        raise RuntimeError("realtime transport unavailable")


class CreateRunRepository:
    def __init__(self):
        self.quiz = {
            "_id": ObjectId(),
            "title": "Onboarding quiz",
            "quiz_type": "multichoice",
            "questions": [{"question": "Q", "answer": "A", "options": ["A", "B"]}],
        }
        self.created_run = None
        self.access_code_checks = 0

    async def get_owned_quiz(self, quiz_id, owner_user_id):
        return self.quiz

    async def access_code_exists_on_run(self, access_code):
        self.access_code_checks += 1
        return False

    async def access_code_exists_on_quiz(self, access_code):
        self.access_code_checks += 1
        return False

    async def create_run(self, payload):
        self.created_run = {**payload, "_id": ObjectId()}
        return self.created_run

    async def create_assignments(self, assignments):
        self.assignments = assignments

    async def create_audit_event(self, event):
        self.audit_event = event

    async def create_invitation_deliveries(self, deliveries):
        self.deliveries = deliveries


class BatchNotificationService:
    def __init__(self):
        self.notified_assignments = None

    async def verified_user_ids_by_email(self, emails):
        return {"learner@example.com": "learner-1"}

    async def notify_assignments(self, assignments, run):
        self.notified_assignments = assignments


class AuthorizationRepository:
    def __init__(self, run=None, assignment=None):
        self.run = run
        self.assignment = assignment

    async def get_run(self, run_id):
        return self.run

    async def get_assignment(self, assignment_id):
        return self.assignment

    async def bind_assignments_to_user(self, recipient_email, user_id):
        return []


class ConcurrentAssignmentsCollection:
    """Makes two reservations read the same attempt count before either updates it."""

    def __init__(self, document):
        self.document = deepcopy(document)
        self._read_count = 0
        self._both_reads_complete = asyncio.Event()

    async def find_one(self, query):
        snapshot = deepcopy(self.document)
        self._read_count += 1
        if self._read_count == 2:
            self._both_reads_complete.set()
        await self._both_reads_complete.wait()
        return snapshot

    async def find_one_and_update(self, query, update, return_document):
        if (
            query["_id"] != self.document["_id"]
            or query["recipient_user_id"] != self.document["recipient_user_id"]
            or query["attempts_used"] != self.document["attempts_used"]
            or self.document["status"] not in query["status"]["$in"]
        ):
            return None
        self.document["attempts_used"] += update["$inc"]["attempts_used"]
        self.document.update(update["$set"])
        return deepcopy(self.document)


class QueryCapturingCursor:
    def sort(self, *_args):
        return self

    def limit(self, _limit):
        return self

    async def to_list(self, *, length):
        return []


class QueryCapturingAssignmentsCollection:
    def __init__(self):
        self.query = None

    def find(self, query):
        self.query = query
        return QueryCapturingCursor()


class ManualCloseRepository:
    def __init__(self):
        self.run = {
            "_id": ObjectId(),
            "quiz_id": "quiz-1",
            "title": "Security training",
            "kind": "compliance",
            "purpose": "health_and_safety",
            "quiz_content_fingerprint": "fingerprint",
            "quiz_snapshot": {"questions": [{"question": "Q"}]},
            "closes_at": datetime.now(timezone.utc) + timedelta(days=1),
            "status": "open",
        }
        self.assignments = [
            {
                "_id": ObjectId(),
                "recipient_email": "learner@example.com",
                "status": "in_progress",
                "attempts_used": 1,
                "max_attempts": 1,
            }
        ]
        self.sessions = [
            {
                "_id": ObjectId(),
                "participant_name": "Learner",
                "status": "active",
            }
        ]
        self.audit_event = None

    async def claim_run_closure(self, run_id, owner_user_id, started_at):
        if self.run.get("closure_in_progress"):
            return None
        self.run = {
            **self.run,
            "closure_in_progress": True,
            "closure_started_at": started_at,
        }
        return self.run

    async def finalize_run_closure(self, run_id, owner_user_id, closed_at):
        if not self.run.get("closure_in_progress"):
            return None
        self.run = {
            **self.run,
            "status": "closed",
            "closed_at": closed_at,
        }
        self.run.pop("closure_in_progress", None)
        self.run.pop("closure_started_at", None)
        return self.run

    async def mark_in_progress_assignments_incomplete(self, run_id, closed_at):
        for assignment in self.assignments:
            if assignment["status"] == "in_progress":
                assignment["status"] = "incomplete"

    async def abandon_active_sessions_for_run(self, run_id, closed_at):
        for session in self.sessions:
            if session["status"] in {"active", "joined", "disconnected"}:
                session["status"] = "abandoned"

    async def list_assignments_for_run(self, run_id):
        return self.assignments

    async def list_sessions_for_run(self, run_id):
        return self.sessions

    async def create_audit_event(self, event):
        self.audit_event = event


def test_assigned_only_training_requires_recipient_and_valid_schedule():
    closes_at = datetime.now(timezone.utc) + timedelta(days=2)
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(quiz_id="quiz-1", closes_at=closes_at)
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            closes_at=closes_at,
            due_at=closes_at + timedelta(days=1),
            recipient_emails=["learner@example.com"],
        )
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            access_mode="public",
            closes_at=closes_at,
            recipient_emails=["learner@example.com"],
        )
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            access_mode="public",
            closes_at=closes_at,
            send_email_invitations=True,
        )
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            kind="compliance",
            access_mode="public",
            closes_at=closes_at,
        )
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            closes_at=closes_at,
            recipient_emails=["learner@example.com"],
            max_attempts=3,
        )
    with pytest.raises(ValidationError, match="title must not contain"):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            closes_at=closes_at,
            recipient_emails=["learner@example.com"],
            title="Legitimate\r\nBcc: injected@example.com",
        )
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            closes_at=closes_at,
            recipient_emails=["learner@example.com"],
            purpose="harassment_prevention",
        )
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1",
            closes_at=datetime.now() + timedelta(days=1),
            recipient_emails=["learner@example.com"],
        )


def test_close_training_run_requires_explicit_confirmation():
    with pytest.raises(ValidationError):
        CloseTrainingRunRequest(confirm=False)
    assert CloseTrainingRunRequest(confirm=True).confirm is True


def test_run_summary_includes_shared_link_attempts_without_merging_assignments():
    service = TrainingRunService(repository=None, live_quiz_service=None)
    run = {
        "_id": "run-1",
        "quiz_id": "quiz-1",
        "title": "Onboarding",
        "kind": "business",
        "purpose": "onboarding",
        "status": "open",
        "access_mode": "public",
        "access_code": "TRAIN123",
        "time_limit_minutes": 20,
        "closes_at": datetime.now(timezone.utc) + timedelta(days=1),
        "created_at": datetime.now(timezone.utc),
    }
    assignments = [{"status": "completed", "latest_score": 8}]
    sessions = [
        {"status": "submitted", "score": 6},
        {"status": "joined", "score": None},
    ]

    summary = service._run_summary(run, assignments, sessions)

    assert summary["assigned_count"] == 1
    assert summary["started_count"] == 3
    assert summary["completed_count"] == 2
    assert summary["average_score"] == 7


@pytest.mark.asyncio
async def test_closed_training_run_rejects_post_close_session_writes(monkeypatch):
    now = datetime(2026, 8, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_session_module, "_utc_now", lambda: now)
    service = LiveQuizSessionService(
        repository=None,
        assignment_repository=FakeAssignmentRepository(
            {"status": "closed", "closes_at": now - timedelta(minutes=1)}
        ),
    )

    with pytest.raises(HTTPException) as error:
        await service._ensure_training_run_open({"training_run_id": "run-1"})

    assert error.value.status_code == 409
    assert error.value.detail == "Training run is closed"


@pytest.mark.asyncio
async def test_manual_closure_claim_blocks_expired_session_finalization(monkeypatch):
    now = datetime(2026, 8, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_session_module, "_utc_now", lambda: now)
    service = LiveQuizSessionService(
        repository=None,
        assignment_repository=FakeAssignmentRepository(
            {
                "status": "open",
                "closure_in_progress": True,
                "closes_at": now + timedelta(minutes=10),
            }
        ),
    )

    with pytest.raises(HTTPException) as error:
        await service._ensure_training_expiry_can_finalize(
            {
                "training_run_id": "run-1",
                "expires_at": now - timedelta(seconds=1),
            }
        )

    assert error.value.status_code == 409
    assert error.value.detail == "Training run is closed"


@pytest.mark.asyncio
async def test_expired_training_session_does_not_mutate_after_scheduled_run_closure(monkeypatch):
    started_at = datetime(2026, 8, 30, tzinfo=timezone.utc)
    now = {"value": started_at}
    monkeypatch.setattr(live_session_module, "_utc_now", lambda: now["value"])
    quiz = {
        "_id": "quiz-1",
        "quiz_type": "multichoice",
        "questions": [{"question": "Q", "answer": "A", "options": ["A", "B"]}],
    }
    repository = FakeTrainingSessionRepository(quiz)
    service = LiveQuizSessionService(
        repository,
        assignment_repository=FakeAssignmentRepository(
            {
                "status": "closed",
                "closes_at": started_at + timedelta(minutes=1),
                "closed_at": started_at + timedelta(minutes=1),
            }
        ),
    )
    started = await service.start_session_for_quiz(
        quiz,
        participant_name="Learner",
        participant_email=None,
        time_limit_minutes=1,
        training_run_id="run-1",
        training_closes_at=started_at + timedelta(minutes=1),
    )

    now["value"] = started_at + timedelta(minutes=1, seconds=1)
    with pytest.raises(HTTPException) as error:
        await service.get_session_state("session-1", started["participant_token"])

    assert error.value.status_code == 409
    assert repository.session["status"] == "joined"


@pytest.mark.asyncio
async def test_realtime_publish_failure_does_not_undo_a_persisted_session():
    quiz = {
        "_id": "quiz-1",
        "quiz_type": "multichoice",
        "questions": [{"question": "Q", "answer": "A", "options": ["A", "B"]}],
    }
    repository = FakeTrainingSessionRepository(quiz)
    service = LiveQuizSessionService(
        repository,
        broadcaster=FailingRealtimeBroadcaster(),
    )

    started = await service.start_session_for_quiz(
        quiz,
        participant_name="Learner",
        participant_email=None,
        time_limit_minutes=20,
        training_run_id="run-1",
        training_assignment_id="assignment-1",
    )

    assert started["session_id"] == "session-1"
    assert repository.session["training_assignment_id"] == "assignment-1"
    assert repository.session["status"] == "joined"


def test_training_start_requires_enough_time_for_the_selected_duration(monkeypatch):
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(training_run_module, "_utc_now", lambda: now)

    with pytest.raises(HTTPException) as error:
        TrainingRunService._ensure_enough_time_to_start(
            {
                "closes_at": now + timedelta(minutes=10),
                "time_limit_minutes": 20,
            }
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_session_creation_rechecks_the_training_close_boundary(monkeypatch):
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(live_session_module, "_utc_now", lambda: now)
    service = LiveQuizSessionService(repository=None)

    with pytest.raises(HTTPException) as error:
        await service.start_session_for_quiz(
            {"_id": "quiz-1", "questions": [{"question": "Q"}]},
            participant_name="Learner",
            participant_email=None,
            time_limit_minutes=20,
            training_closes_at=now + timedelta(minutes=19),
        )

    assert error.value.status_code == 409
    assert error.value.detail == "There is not enough time left to complete this training before it closes"


@pytest.mark.asyncio
async def test_training_run_uses_its_immutable_quiz_snapshot():
    service = TrainingRunService(repository=None, live_quiz_service=None)
    run = {
        "quiz_id": "quiz-1",
        "owner_user_id": "owner-1",
        "quiz_snapshot": {
            "title": "Onboarding snapshot",
            "quiz_type": "multichoice",
            "questions": [{"question": "Q", "correct_answer": "A", "options": ["A", "B"]}],
        },
    }

    quiz = await service._quiz_for_run(run)
    quiz["questions"][0]["question"] = "Changed while delivering"
    stored_snapshot = run["quiz_snapshot"]

    assert quiz["title"] == "Onboarding snapshot"
    assert quiz["questions"][0]["correct_answer"] == "A"
    assert stored_snapshot["questions"][0]["question"] == "Q"


def test_in_progress_assignment_is_not_presented_as_retryable():
    now = datetime.now(timezone.utc)
    service = TrainingRunService(repository=None, live_quiz_service=None)
    summary = service._assignment_summary(
        {
            "_id": "assignment-1",
            "training_run_id": "run-1",
            "quiz_id": "quiz-1",
            "recipient_email": "learner@example.com",
            "status": "in_progress",
            "attempts_used": 1,
            "max_attempts": 2,
        },
        {
            "_id": "run-1",
            "title": "Training",
            "kind": "business",
            "purpose": "onboarding",
            "status": "open",
            "time_limit_minutes": 20,
            "closes_at": now + timedelta(hours=1),
        },
    )

    assert summary["can_retry"] is False


def test_assignment_is_not_presented_as_startable_at_the_exact_close_boundary(monkeypatch):
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(training_run_module, "_utc_now", lambda: now)
    service = TrainingRunService(repository=None, live_quiz_service=None)
    summary = service._assignment_summary(
        {
            "_id": "assignment-1",
            "training_run_id": "run-1",
            "quiz_id": "quiz-1",
            "recipient_email": "learner@example.com",
            "status": "assigned",
            "attempts_used": 0,
            "max_attempts": 1,
        },
        {
            "_id": "run-1",
            "title": "Training",
            "kind": "business",
            "purpose": "onboarding",
            "status": "open",
            "time_limit_minutes": 20,
            "closes_at": now + timedelta(minutes=20),
        },
    )

    assert summary["can_retry"] is False


@pytest.mark.asyncio
async def test_new_run_requires_a_full_duration_before_its_close_time(monkeypatch):
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(training_run_module, "_utc_now", lambda: now)
    payload = type(
        "Payload",
        (),
        {
            "closes_at": now + timedelta(minutes=20),
            "due_at": None,
            "time_limit_minutes": 20,
        },
    )()

    service = TrainingRunService(repository=None, live_quiz_service=None)
    with pytest.raises(HTTPException) as error:
        # The pre-repository check protects a newly-created unusable run.
        await service.create_run(payload, "owner-1")

    assert error.value.status_code == 400
    assert error.value.detail == "Run close time must allow one full training duration"


@pytest.mark.asyncio
async def test_assigned_only_run_does_not_generate_an_unused_access_code():
    repository = CreateRunRepository()
    service = TrainingRunService(repository, live_quiz_service=None)
    payload = CreateTrainingRunRequest(
        quiz_id=str(repository.quiz["_id"]),
        closes_at=datetime.now(timezone.utc) + timedelta(days=2),
        recipient_emails=["learner@example.com"],
    )

    summary = await service.create_run(payload, "owner-1")

    assert repository.created_run["access_code"] is None
    assert repository.access_code_checks == 0
    assert summary["access_code"] is None
    assert summary["access_url"] is None


@pytest.mark.asyncio
async def test_legacy_quiz_title_cannot_poison_training_email_headers():
    repository = CreateRunRepository()
    repository.quiz["title"] = "Legitimate\r\nBcc: injected@example.com"
    service = TrainingRunService(repository, live_quiz_service=None)
    payload = CreateTrainingRunRequest(
        quiz_id=str(repository.quiz["_id"]),
        closes_at=datetime.now(timezone.utc) + timedelta(days=2),
        recipient_emails=["learner@example.com"],
    )

    with pytest.raises(HTTPException, match="Training title") as error:
        await service.create_run(payload, "owner-1")

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_legacy_quiz_title_cannot_exceed_training_title_limit():
    repository = CreateRunRepository()
    repository.quiz["title"] = "x" * 181
    service = TrainingRunService(repository, live_quiz_service=None)
    payload = CreateTrainingRunRequest(
        quiz_id=str(repository.quiz["_id"]),
        closes_at=datetime.now(timezone.utc) + timedelta(days=2),
        recipient_emails=["learner@example.com"],
    )

    with pytest.raises(HTTPException, match="must not exceed") as error:
        await service.create_run(payload, "owner-1")

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_training_invitation_email_is_persisted_then_dispatched(monkeypatch):
    repository = CreateRunRepository()
    notifications = BatchNotificationService()
    send_task = []
    from server.celery_config import celery_app

    monkeypatch.setattr(
        celery_app,
        "send_task",
        lambda *args, **kwargs: send_task.append((args, kwargs)),
    )
    service = TrainingRunService(
        repository,
        live_quiz_service=None,
        notification_service=notifications,
    )
    payload = CreateTrainingRunRequest(
        quiz_id=str(repository.quiz["_id"]),
        closes_at=datetime.now(timezone.utc) + timedelta(days=2),
        recipient_emails=["learner@example.com"],
        send_email_invitations=True,
    )

    await service.create_run(payload, "owner-1")

    assert len(notifications.notified_assignments) == 1
    assert len(repository.deliveries) == 1
    assert repository.deliveries[0]["status"] == "pending"
    assert repository.deliveries[0]["recipient_email"] == "learner@example.com"
    assert send_task == [
        (
            ("tasks.dispatch_training_invitation_deliveries",),
            {"queue": "email", "ignore_result": True},
        )
    ]


@pytest.mark.asyncio
async def test_training_run_owner_endpoints_hide_other_owners_runs():
    run = {"_id": "run-1", "owner_user_id": "owner-1"}
    service = TrainingRunService(
        AuthorizationRepository(run=run), live_quiz_service=None
    )

    with pytest.raises(HTTPException) as get_error:
        await service.get_owner_run("run-1", "owner-2")
    with pytest.raises(HTTPException) as close_error:
        await service.close_owner_run("run-1", "owner-2")

    assert get_error.value.status_code == 404
    assert close_error.value.status_code == 404


@pytest.mark.asyncio
async def test_training_assignment_start_hides_other_recipients_assignments():
    service = TrainingRunService(
        AuthorizationRepository(
            assignment={
                "_id": "assignment-1",
                "recipient_user_id": "recipient-1",
                "training_run_id": "run-1",
            }
        ),
        live_quiz_service=None,
    )
    user = SimpleNamespace(
        id="recipient-2",
        email="recipient-2@example.com",
        full_name="Recipient Two",
        username="recipient-two",
    )

    with pytest.raises(HTTPException) as error:
        await service.start_assignment("assignment-1", user)

    assert error.value.status_code == 404
    assert error.value.detail == "Training assignment not found"


@pytest.mark.asyncio
async def test_assignment_email_fallback_only_includes_unclaimed_assignments():
    assignments_collection = QueryCapturingAssignmentsCollection()
    repository = TrainingRunRepository(
        quizzes_collection=None,
        runs_collection=None,
        assignments_collection=assignments_collection,
        audit_events_collection=None,
    )

    await repository.list_assignments_for_recipient(
        "learner@example.com", "learner-1"
    )

    assert assignments_collection.query == {
        "$or": [
            {"recipient_user_id": "learner-1"},
            {
                "recipient_email": "learner@example.com",
                "recipient_user_id": None,
            },
        ]
    }


@pytest.mark.asyncio
async def test_reserve_attempt_allows_only_one_concurrent_last_attempt():
    assignment = {
        "_id": ObjectId(),
        "recipient_user_id": "recipient-1",
        "status": "assigned",
        "attempts_used": 0,
        "max_attempts": 1,
    }
    assignments_collection = ConcurrentAssignmentsCollection(assignment)
    repository = TrainingRunRepository(
        quizzes_collection=None,
        runs_collection=None,
        assignments_collection=assignments_collection,
        audit_events_collection=None,
    )
    now = datetime.now(timezone.utc)

    first, second = await asyncio.gather(
        repository.reserve_attempt(str(assignment["_id"]), "recipient-1", now),
        repository.reserve_attempt(str(assignment["_id"]), "recipient-1", now),
    )

    assert sum(result is not None for result in (first, second)) == 1
    assert assignments_collection.document["attempts_used"] == 1
    assert assignments_collection.document["status"] == "in_progress"


@pytest.mark.asyncio
async def test_reserve_attempt_rejects_concurrent_attempt_while_in_progress():
    class InProgressAssignmentCollection:
        def __init__(self, document):
            self.document = deepcopy(document)
            self.last_reservation_query = None

        async def find_one(self, _query):
            return deepcopy(self.document)

        async def find_one_and_update(self, query, _update, return_document):
            self.last_reservation_query = query
            return None

    assignment = {
        "_id": ObjectId(),
        "recipient_user_id": "recipient-1",
        "status": "in_progress",
        "attempts_used": 1,
        "max_attempts": 2,
    }
    assignments_collection = InProgressAssignmentCollection(assignment)
    repository = TrainingRunRepository(
        quizzes_collection=None,
        runs_collection=None,
        assignments_collection=assignments_collection,
        audit_events_collection=None,
    )

    reservation = await repository.reserve_attempt(
        str(assignment["_id"]), "recipient-1", datetime.now(timezone.utc)
    )

    assert reservation is None
    assert assignments_collection.document["attempts_used"] == 1
    assert assignments_collection.document["status"] == "in_progress"
    assert "in_progress" not in assignments_collection.last_reservation_query["status"]["$in"]


@pytest.mark.asyncio
async def test_public_access_stops_at_close_time_before_background_closure(monkeypatch):
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(training_run_module, "_utc_now", lambda: now)
    run = {
        "_id": "run-1",
        "status": "open",
        "access_mode": "public",
        "closes_at": now,
    }

    class PublicRunRepository:
        async def get_run_by_access_code(self, access_code):
            return run

        async def get_run(self, run_id):
            return run

    service = TrainingRunService(PublicRunRepository(), live_quiz_service=None)

    with pytest.raises(HTTPException) as error:
        await service.access_preview("PUBLIC123")

    assert error.value.status_code == 410
    assert error.value.detail == "Training run is closed"


@pytest.mark.asyncio
async def test_manual_close_marks_active_attempts_incomplete_before_audit_snapshot():
    repository = ManualCloseRepository()
    service = TrainingRunService(repository, live_quiz_service=None)

    closed = await service._close_run(repository.run, "owner-1")

    assert closed["status"] == "closed"
    assert repository.assignments[0]["status"] == "incomplete"
    assert repository.sessions[0]["status"] == "abandoned"
    completion_register = repository.audit_event["payload"]["completion_register"]
    assert completion_register[0]["status"] == "incomplete"
    assert completion_register[1]["status"] == "abandoned"


@pytest.mark.asyncio
async def test_manual_close_keeps_its_claim_when_audit_persistence_fails():
    repository = ManualCloseRepository()

    async def fail_audit(_event):
        raise RuntimeError("audit storage unavailable")

    repository.create_audit_event = fail_audit
    service = TrainingRunService(repository, live_quiz_service=None)

    with pytest.raises(RuntimeError, match="audit storage unavailable"):
        await service._close_run(repository.run, "owner-1")

    assert repository.run["status"] == "open"
    assert repository.run["closure_in_progress"] is True


@pytest.mark.asyncio
async def test_manual_close_keeps_its_claim_when_finalization_fails_after_audit():
    repository = ManualCloseRepository()

    async def fail_finalization(_run_id, _owner_user_id, _closed_at):
        return None

    repository.finalize_run_closure = fail_finalization
    service = TrainingRunService(repository, live_quiz_service=None)

    with pytest.raises(RuntimeError, match="could not be finalized"):
        await service._close_run(repository.run, "owner-1")

    assert repository.audit_event is not None
    assert repository.run["status"] == "open"
    assert repository.run["closure_in_progress"] is True
