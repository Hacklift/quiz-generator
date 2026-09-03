from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import server.app.quiz.services.live_session_service as live_session_module
import server.app.quiz.services.training_run_service as training_run_module
from server.app.quiz.schemas.training_runs import (
    CloseTrainingRunRequest,
    CreateTrainingRunRequest,
)
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.services.training_run_service import TrainingRunService


class FakeAssignmentRepository:
    def __init__(self, run):
        self.run = run

    async def get_run(self, run_id):
        return self.run if run_id == "run-1" else None


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
