from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import server.app.quiz.services.live_session_service as live_quiz_session_service
from server.app.quiz.services.live_session_service import LiveQuizSessionService


class FakeLiveQuizRepository:
    def __init__(self, time_limit_minutes: int):
        self.quiz = {
            "_id": "quiz-1",
            "title": "Timing Quiz",
            "live_quiz_enabled": True,
            "time_limit_minutes": time_limit_minutes,
            "access_code_expires_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "questions": [
                {
                    "question": "Question 1",
                    "options": ["A", "B"],
                    "answer": "A",
                    "question_type": "multichoice",
                }
            ],
        }
        self.session = None

    async def get_quiz_by_access_code(self, access_code):
        return self.quiz

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

    async def save_answer(self, session_id, question_index, selected_answer, next_question_index=None):
        answers = [a for a in self.session.get("answers", []) if a["question_index"] != question_index]
        answers.append({"question_index": question_index, "selected_answer": selected_answer, "answered_at": datetime.now(timezone.utc)})
        self.session["answers"] = answers
        if next_question_index is not None:
            self.session["current_question_index"] = next_question_index
        return self.session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("time_limit_minutes", "expected_seconds"),
    [(1, 60), (2, 120), (10, 600), (20, 1200), (27, 1620), (60, 3600)],
)
async def test_start_session_treats_time_limit_as_minutes(
    monkeypatch,
    time_limit_minutes,
    expected_seconds,
):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    service = LiveQuizSessionService(FakeLiveQuizRepository(time_limit_minutes))

    response = await service.start_session(
        code="ABC123",
        participant_name="Ada",
        participant_email="ada@example.com",
    )

    assert response["started_at"] == fixed_now
    assert response["expires_at"] == fixed_now + timedelta(minutes=time_limit_minutes)
    assert response["server_now"] == fixed_now
    assert response["time_limit_minutes"] == time_limit_minutes
    assert response["duration_seconds"] == expected_seconds
    assert response["remaining_seconds"] == expected_seconds


@pytest.mark.asyncio
async def test_auto_submit_does_not_expire_before_expires_at(monkeypatch):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    current_time = {"value": fixed_now}
    monkeypatch.setattr(
        live_quiz_session_service,
        "_utc_now",
        lambda: current_time["value"],
    )

    repository = FakeLiveQuizRepository(time_limit_minutes=1)
    service = LiveQuizSessionService(repository)
    start_response = await service.start_session(
        code="ABC123",
        participant_name="Ada",
        participant_email=None,
    )

    state = await service.get_session_state(
        "session-1",
        start_response["participant_token"],
    )
    assert state["status"] == "active"
    assert state["remaining_seconds"] == 60

    current_time["value"] = fixed_now + timedelta(seconds=59)
    with pytest.raises(HTTPException) as exc:
        await service.submit_session(
            "session-1",
            start_response["participant_token"],
            auto_submitted=True,
        )

    assert exc.value.status_code == 409
    assert repository.session["status"] == "joined"


@pytest.mark.asyncio
async def test_auto_submit_expires_after_expires_at(monkeypatch):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    current_time = {"value": fixed_now}
    monkeypatch.setattr(
        live_quiz_session_service,
        "_utc_now",
        lambda: current_time["value"],
    )

    repository = FakeLiveQuizRepository(time_limit_minutes=1)
    service = LiveQuizSessionService(repository)
    service._grade_session = lambda session, quiz: {"score": 0, "percentage": 0}

    start_response = await service.start_session(
        code="ABC123",
        participant_name="Ada",
        participant_email=None,
    )
    current_time["value"] = fixed_now + timedelta(seconds=60)

    response = await service.submit_session(
        "session-1",
        start_response["participant_token"],
        auto_submitted=True,
    )

    assert response["status"] == "submitted"
    assert response["auto_submitted"] is True
    assert repository.session["submitted_at"] == current_time["value"]


@pytest.mark.asyncio
async def test_session_state_auto_submits_after_expires_at(monkeypatch):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    current_time = {"value": fixed_now}
    monkeypatch.setattr(
        live_quiz_session_service,
        "_utc_now",
        lambda: current_time["value"],
    )

    repository = FakeLiveQuizRepository(time_limit_minutes=1)
    service = LiveQuizSessionService(repository)
    service._grade_session = lambda session, quiz: {"score": 0, "percentage": 0}

    start_response = await service.start_session(
        code="ABC123",
        participant_name="Ada",
        participant_email=None,
    )
    current_time["value"] = fixed_now + timedelta(seconds=61)

    state = await service.get_session_state(
        "session-1",
        start_response["participant_token"],
    )

    assert state["status"] == "submitted"
    assert state["auto_submitted"] is True
    assert state["remaining_seconds"] == 0


@pytest.mark.asyncio
async def test_duplicate_submit_returns_idempotent_response(monkeypatch):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    current_time = {"value": fixed_now}
    monkeypatch.setattr(
        live_quiz_session_service,
        "_utc_now",
        lambda: current_time["value"],
    )

    repository = FakeLiveQuizRepository(time_limit_minutes=1)
    service = LiveQuizSessionService(repository)
    service._grade_session = lambda session, quiz: {"score": 0, "percentage": 0}

    start_response = await service.start_session(
        code="ABC123",
        participant_name="Ada",
        participant_email=None,
    )
    current_time["value"] = fixed_now + timedelta(seconds=60)
    await service.submit_session(
        "session-1",
        start_response["participant_token"],
        auto_submitted=True,
    )

    response = await service.submit_session(
        "session-1",
        start_response["participant_token"],
        auto_submitted=True,
    )

    assert response["status"] == "already_submitted"
    assert response["submitted_at"] == current_time["value"]


class FakeAssignmentRepository:
    def __init__(self, run: dict):
        self.run = run

    async def get_run(self, run_id: str):
        return self.run


@pytest.mark.asyncio
async def test_session_state_releases_answers_and_explanations_immediately_by_default(monkeypatch):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repo = FakeLiveQuizRepository(time_limit_minutes=1)
    repo.quiz["questions"][0]["explanation"] = "Because A is the premier option."
    service = LiveQuizSessionService(repo)

    start = await service.start_session(code="ABC123", participant_name="Sam", participant_email=None)
    await service.save_answer("session-1", start["participant_token"], question_index=0, selected_answer="A")
    await service.submit_session("session-1", start["participant_token"])

    state = await service.get_session_state("session-1", start["participant_token"])
    assert state["status"] == "submitted"
    assert state["answers_released"] is True
    assert state["release_answers_at"] is None
    assert len(state["graded_answers"]) == 1
    assert state["graded_answers"][0]["is_correct"] is True
    assert state["graded_answers"][0]["correct_answer"] == "A"
    assert state["graded_answers"][0]["explanation"] == "Because A is the premier option."


@pytest.mark.asyncio
async def test_session_state_withholds_answers_when_assignment_window_is_open(monkeypatch):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    window_close = datetime(2025, 5, 14, 12, 00, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repo = FakeLiveQuizRepository(time_limit_minutes=1)
    repo.quiz["questions"][0]["explanation"] = "Secret explanation."
    assignment_repo = FakeAssignmentRepository({
        "status": "open",
        "closes_at": window_close,
        "release_answers": "after_close",
    })
    service = LiveQuizSessionService(repo, assignment_repository=assignment_repo)

    start = await service.start_session(code="ABC123", participant_name="Sam", participant_email=None)
    repo.session["training_run_id"] = "run-1"
    await service.save_answer("session-1", start["participant_token"], question_index=0, selected_answer="B")
    await service.submit_session("session-1", start["participant_token"])

    state = await service.get_session_state("session-1", start["participant_token"])
    assert state["status"] == "submitted"
    assert state["answers_released"] is False
    assert state["release_answers_at"] == window_close
    assert len(state["graded_answers"]) == 1
    # Answers and explanations are withheld
    assert state["graded_answers"][0]["correct_answer"] == ""
    assert state["graded_answers"][0]["explanation"] is None

