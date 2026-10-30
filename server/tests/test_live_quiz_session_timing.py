from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import server.app.quiz.services.live_session_service as live_quiz_session_service
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.schemas.live_session_schemas import LiveQuizSessionState


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

    async def save_answer(
        self,
        session_id,
        question_index,
        selected_answer,
        next_question_index,
    ):
        answers = [
            answer
            for answer in self.session.get("answers", [])
            if answer["question_index"] != question_index
        ]
        answers.append(
            {
                "question_index": question_index,
                "selected_answer": selected_answer,
                "answered_at": datetime.now(timezone.utc),
            }
        )
        self.session = {
            **self.session,
            "answers": answers,
            "current_question_index": next_question_index,
            "status": "active",
        }
        return self.session


@pytest.mark.asyncio
async def test_matching_answer_survives_save_reload_and_response_validation(
    monkeypatch,
):
    fixed_now = datetime(2025, 5, 14, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)
    repository = FakeLiveQuizRepository(time_limit_minutes=20)
    repository.quiz["quiz_type"] = "matching"
    repository.quiz["questions"] = [
        {
            "question": "Match each country to its capital.",
            "answer": {"France": "Paris", "Italy": "Rome"},
            "question_type": "matching",
        }
    ]
    service = LiveQuizSessionService(repository)
    started = await service.start_session(
        code="ABC123",
        participant_name="Ada",
        participant_email=None,
    )
    selected_answer = {"France": "Paris", "Italy": "Rome"}

    await service.save_answer(
        "session-1",
        started["participant_token"],
        question_index=0,
        selected_answer=selected_answer,
    )
    state = await service.get_session_state("session-1", started["participant_token"])
    response = LiveQuizSessionState.model_validate(state)

    assert response.question is not None
    assert response.question.selected_answer == selected_answer
    assert response.answers[0].selected_answer == selected_answer


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
