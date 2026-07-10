"""Tests for live quiz analytics / creator dashboard functionality.

Tests cover:
- participant joins timed quiz
- participant submits quiz
- creator can fetch updated participant list
- non-owner cannot fetch participant list
- score appears after submission
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from bson import ObjectId
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect

import server.app.quiz.services.live_session_service as live_quiz_session_service
from server.app.core.config import settings
from server.app.quiz.routes import live_sessions as live_sessions_routes
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.users.models import UserOut


class FakeAnalyticsRepository:
    def __init__(self):
        self.creator_id = "creator-1"
        self.quiz = {
            "_id": "quiz-1",
            "title": "Analytics Quiz",
            "created_by": self.creator_id,
            "live_quiz_enabled": True,
            "time_limit_minutes": 10,
            "access_code_expires_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "questions": [
                {
                    "question": "Q1",
                    "options": ["A", "B"],
                    "answer": "A",
                    "question_type": "multichoice",
                },
                {
                    "question": "Q2",
                    "options": ["A", "B"],
                    "answer": "B",
                    "question_type": "multichoice",
                },
            ],
        }
        self.sessions = {}
        self.session_counter = 0

    async def get_quiz_by_access_code(self, access_code):
        return self.quiz

    async def create_session(self, session_data):
        self.session_counter += 1
        session_id = f"session-{self.session_counter}"
        session = {**session_data, "_id": session_id}
        self.sessions[session_id] = session
        return session_id

    async def get_session(self, session_id):
        return self.sessions.get(session_id)

    async def get_quiz_by_id(self, quiz_id):
        return self.quiz

    async def update_session(self, session_id, updates):
        if session_id in self.sessions:
            self.sessions[session_id] = {**self.sessions[session_id], **updates}
        return self.sessions.get(session_id)

    async def save_answer(
        self,
        session_id,
        question_index,
        selected_answer,
        next_question_index,
    ):
        session = self.sessions.get(session_id)
        if not session:
            return None
        answers = [
            answer
            for answer in session.get("answers", [])
            if answer.get("question_index") != question_index
        ]
        answers.append(
            {
                "question_index": question_index,
                "selected_answer": selected_answer,
                "answered_at": datetime.now(timezone.utc),
            }
        )
        session.update(
            {
                "answers": answers,
                "current_question_index": next_question_index,
                "status": "active",
            }
        )
        return session

    async def list_quiz_sessions(self, quiz_id):
        """Match the real repository's method signature."""
        return [
            sess for sess in self.sessions.values()
            if sess.get("quiz_id") == quiz_id
        ]


@pytest.mark.asyncio
async def test_participant_joins_and_appears_in_analytics(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repository = FakeAnalyticsRepository()
    service = LiveQuizSessionService(repository)

    await service.start_session(
        code="ABC123",
        participant_name="Alice",
        participant_email="alice@example.com",
    )

    rows = await service.list_analytics("quiz-1", "creator-1")
    assert len(rows) == 1
    assert rows[0]["participant_name"] == "Alice"
    assert rows[0]["participant_email"] == "alice@example.com"
    assert rows[0]["status"] == "joined"
    assert rows[0]["started_at"] == fixed_now
    assert rows[0]["score"] is None
    assert rows[0]["submitted_at"] is None


@pytest.mark.asyncio
async def test_participant_submits_and_score_appears_in_analytics(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    current_time = {"value": fixed_now}
    monkeypatch.setattr(
        live_quiz_session_service,
        "_utc_now",
        lambda: current_time["value"],
    )

    repository = FakeAnalyticsRepository()
    service = LiveQuizSessionService(repository)

    # Start session
    start_resp = await service.start_session(
        code="ABC123",
        participant_name="Bob",
        participant_email="bob@example.com",
    )

    # Fast-forward past time limit
    current_time["value"] = fixed_now + timedelta(minutes=10)

    # Submit
    await service.submit_session(
        start_resp["session_id"],
        start_resp["participant_token"],
        auto_submitted=True,
    )

    rows = await service.list_analytics("quiz-1", "creator-1")
    assert len(rows) == 1
    assert rows[0]["participant_name"] == "Bob"
    assert rows[0]["status"] == "timed_out"
    assert rows[0]["submitted_at"] == current_time["value"]
    assert rows[0]["score"] is not None
    assert rows[0]["total_questions"] == 2


@pytest.mark.asyncio
async def test_non_owner_cannot_fetch_analytics(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repository = FakeAnalyticsRepository()
    service = LiveQuizSessionService(repository)

    # Non-creator user
    with pytest.raises(HTTPException) as exc:
        await service.list_analytics("quiz-1", "intruder-1")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_analytics_shows_multiple_participants(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    current_time = {"value": fixed_now}
    monkeypatch.setattr(
        live_quiz_session_service,
        "_utc_now",
        lambda: current_time["value"],
    )

    repository = FakeAnalyticsRepository()
    service = LiveQuizSessionService(repository)

    # Participant 1 joins and submits
    r1 = await service.start_session("ABC123", "Alice", "alice@example.com")
    current_time["value"] = fixed_now + timedelta(minutes=10)
    await service.submit_session(r1["session_id"], r1["participant_token"], auto_submitted=True)

    # Participant 2 joins but does not submit yet (starts at minute 5)
    current_time["value"] = fixed_now + timedelta(minutes=5)
    r2 = await service.start_session("ABC123", "Bob", None)

    # Participant 3 joins at minute 5, submits at minute 15 (after 10min time limit expires)
    r3 = await service.start_session("ABC123", "Charlie", "charlie@example.com")
    current_time["value"] = fixed_now + timedelta(minutes=15)
    await service.submit_session(r3["session_id"], r3["participant_token"], auto_submitted=True)

    rows = await service.list_analytics("quiz-1", "creator-1")
    assert len(rows) == 3

    alice = next(r for r in rows if r["participant_name"] == "Alice")
    bob = next(r for r in rows if r["participant_name"] == "Bob")
    charlie = next(r for r in rows if r["participant_name"] == "Charlie")

    assert alice["status"] == "timed_out"
    assert alice["score"] is not None
    assert alice["submitted_at"] is not None

    assert bob["status"] == "joined"
    assert bob["score"] is None
    assert bob["submitted_at"] is None

    assert charlie["status"] == "timed_out"
    assert charlie["score"] is not None
    assert charlie["submitted_at"] is not None


@pytest.mark.asyncio
async def test_empty_analytics_before_any_participants(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repository = FakeAnalyticsRepository()
    service = LiveQuizSessionService(repository)

    rows = await service.list_analytics("quiz-1", "creator-1")
    assert rows == []


@pytest.mark.asyncio
async def test_answer_progress_updates_status_and_percent(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repository = FakeAnalyticsRepository()
    service = LiveQuizSessionService(repository)

    start_resp = await service.start_session(
        code="ABC123",
        participant_name="Dana",
        participant_email="dana@example.com",
    )
    await service.save_answer(
        start_resp["session_id"],
        start_resp["participant_token"],
        question_index=0,
        selected_answer="A",
        next_question_index=1,
    )

    rows = await service.list_analytics("quiz-1", "creator-1")
    assert rows[0]["status"] == "in_progress"
    assert rows[0]["progress"] == 1
    assert rows[0]["current_question_number"] == 2
    assert rows[0]["progress_percentage"] == 50


class FakeAccessCodeRepository:
    def __init__(self):
        self.quiz = {
            "_id": "quiz-1",
            "title": "Invitation Quiz",
            "owner_user_id": "creator-1",
            "questions": [{"question": "Q1", "answer": "A"}],
        }
        self.updated = None
        self.enable_calls = 0

    async def get_quiz_by_id(self, quiz_id):
        return self.quiz

    async def access_code_exists(self, access_code):
        return False

    async def enable_live_quiz(self, **kwargs):
        self.enable_calls += 1
        self.updated = kwargs
        self.quiz = {
            **self.quiz,
            "live_quiz_enabled": True,
            "access_code": kwargs["access_code"],
            "time_limit_minutes": kwargs["time_limit_minutes"],
            "access_code_expires_at": kwargs["access_code_expires_at"],
            "participant_access_mode": kwargs["participant_access_mode"],
            "invited_participant_emails": kwargs["invited_participant_emails"],
        }
        return self.quiz


class FakeExistingAccessCodeRepository(FakeAccessCodeRepository):
    def __init__(self):
        super().__init__()
        self.quiz.update(
            {
                "live_quiz_enabled": True,
                "access_code": "KEEP42",
                "time_limit_minutes": 20,
                "access_code_expires_at": datetime(2025, 6, 2, tzinfo=timezone.utc),
                "participant_access_mode": "public",
                "invited_participant_emails": [],
            }
        )


class FakeAccessCodeLifecycleRepository(FakeExistingAccessCodeRepository):
    async def get_quiz_by_access_code(self, access_code):
        if access_code == self.quiz.get("access_code"):
            return self.quiz
        return None


class FakeCreatorLiveQuizzesRepository:
    def __init__(self):
        self.quizzes = [
            {
                "_id": "quiz-1",
                "title": "Management Quiz",
                "access_code": "LIVE01",
                "access_code_expires_at": datetime(2025, 6, 2, tzinfo=timezone.utc),
                "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
            }
        ]
        self.sessions = [
            {
                "_id": "session-1",
                "quiz_id": "quiz-1",
                "participant_name": "Alice",
                "status": "submitted",
                "submitted_at": datetime(2025, 6, 1, 10, 5, tzinfo=timezone.utc),
                "score": 2,
                "total_questions": 2,
                "answers": [],
            },
            {
                "_id": "session-2",
                "quiz_id": "quiz-1",
                "participant_name": "Bob",
                "status": "active",
                "submitted_at": None,
                "score": None,
                "total_questions": 2,
                "answers": [],
            },
        ]

    async def list_live_quizzes_by_creator(self, creator_user_id):
        return self.quizzes

    async def list_quiz_sessions(self, quiz_id):
        return [
            session for session in self.sessions if session.get("quiz_id") == quiz_id
        ]

    async def get_quiz_by_id(self, quiz_id):
        return {
            "_id": quiz_id,
            "created_by": "creator-1",
            "questions": [{"question": "Q1", "answer": "A"}],
        }


class FakeInvitationRepository:
    def __init__(self):
        self.invitations = []
        self.deliveries = []

    async def upsert_invitation(self, invitation):
        self.invitations.append(invitation)
        return f"inv-{len(self.invitations)}"

    async def update_email_delivery(self, invitation_id, **kwargs):
        self.deliveries.append({"invitation_id": invitation_id, **kwargs})


class FakeEmailService:
    def __init__(self):
        self.sent = []

    async def send_email(self, **kwargs):
        self.sent.append(kwargs)
        return SimpleNamespace(ok=True, adapter="background")


@pytest.mark.asyncio
async def test_generate_access_code_creates_and_sends_invitations(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)
    monkeypatch.setattr(
        live_quiz_session_service.settings,
        "FRONTEND_BASE_URL",
        "https://quiz.example",
    )

    invitation_repository = FakeInvitationRepository()
    email_service = FakeEmailService()
    service = LiveQuizSessionService(FakeAccessCodeRepository())

    response = await service.generate_access_code(
        quiz_id="quiz-1",
        access_code_expires_at=fixed_now + timedelta(days=1),
        creator_id="creator-1",
        time_limit_minutes=15,
        participant_access_mode="restricted",
        invited_emails=["ADA@example.com", "grace@example.com"],
        send_email_invitations=True,
        invitation_repository=invitation_repository,
        email_service=email_service,
    )

    assert response["invitations_created"] == 2
    assert response["invitations_queued"] == 2
    assert response["invitations_delivered"] == 0
    assert response["invited_emails"] == ["ada@example.com", "grace@example.com"]
    assert invitation_repository.invitations[0]["status"] == "pending"
    assert invitation_repository.deliveries[0]["status"] == "queued"
    assert len(email_service.sent) == 2
    assert "https://quiz.example/quiz-access/" in email_service.sent[0]["template_vars"]["body"]


@pytest.mark.asyncio
async def test_generate_access_code_route_uses_configured_frontend_url(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)
    monkeypatch.setattr(
        live_quiz_session_service.settings,
        "FRONTEND_BASE_URL",
        "https://trusted.example",
    )

    invitation_repository = FakeInvitationRepository()
    email_service = FakeEmailService()
    service = LiveQuizSessionService(FakeAccessCodeRepository())
    payload = live_sessions_routes.AccessCodeCreateRequest(
        time_limit_minutes=15,
        access_code_expires_at=fixed_now + timedelta(days=1),
        participant_access_mode="restricted",
        invited_emails=["ada@example.com"],
        send_email_invitations=True,
    )
    current_user = UserOut(
        id="creator-1",
        username="creator",
        email="creator@example.com",
        is_verified=True,
        status="active",
    )

    await live_sessions_routes.generate_quiz_access_code(
        quiz_id="quiz-1",
        payload=payload,
        current_user=current_user,
        service=service,
        invitation_repository=invitation_repository,
        email_service=email_service,
    )

    body = email_service.sent[0]["template_vars"]["body"]
    assert "https://trusted.example/quiz-access/" in body
    assert "https://attacker.example" not in body


class FakeWebSocket:
    def __init__(self, auth_message):
        self.auth_message = auth_message
        self.accepted = False
        self.close_code = None
        self.sent_json = []

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        return self.auth_message

    async def close(self, code):
        self.close_code = code

    async def send_json(self, payload):
        self.sent_json.append(payload)

    async def receive_text(self):
        raise WebSocketDisconnect()


@pytest.mark.asyncio
async def test_live_quiz_websocket_rejects_missing_auth_message():
    websocket = FakeWebSocket({"type": "authenticate"})

    await live_sessions_routes.live_quiz_participants_ws(
        websocket,
        "quiz-1",
        service=object(),
        users_collection=object(),
        sessions_collection=object(),
    )

    assert websocket.accepted is True
    assert websocket.close_code == 1008
    assert websocket.sent_json == []


@pytest.mark.asyncio
async def test_live_quiz_websocket_authenticates_with_first_message():
    user_id = ObjectId()
    user = {
        "_id": user_id,
        "username": "creator",
        "email": "creator@example.com",
        "is_active": True,
        "is_verified": True,
        "status": "active",
        "created_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
    }
    token = jwt.encode(
        {
            "sub": str(user_id),
            "jti": "jti-1",
            "sid": "session-1",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    class FakeCollection:
        async def find_one(self, query):
            if query.get("_id") == user_id:
                return user
            if query.get("session_id") == "session-1":
                return {"session_id": "session-1", "user_id": str(user_id)}
            return None

        async def update_one(self, *_args, **_kwargs):
            return None

    class FakeLiveQuizService:
        async def list_analytics(self, quiz_id, creator_id):
            assert quiz_id == "quiz-1"
            assert creator_id == str(user_id)
            return []

    websocket = FakeWebSocket({"type": "authenticate", "token": token})

    await live_sessions_routes.live_quiz_participants_ws(
        websocket,
        "quiz-1",
        service=FakeLiveQuizService(),
        users_collection=FakeCollection(),
        sessions_collection=FakeCollection(),
    )

    assert websocket.close_code is None
    assert websocket.sent_json == [
        {
            "type": "participants_snapshot",
            "quiz_id": "quiz-1",
            "participants": [],
        }
    ]


@pytest.mark.asyncio
async def test_generate_access_code_returns_existing_code_without_regenerating(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repository = FakeExistingAccessCodeRepository()
    service = LiveQuizSessionService(repository)

    response = await service.generate_access_code(
        quiz_id="quiz-1",
        access_code_expires_at=fixed_now + timedelta(days=7),
        creator_id="creator-1",
        time_limit_minutes=30,
    )

    assert response["access_code"] == "KEEP42"
    assert response["time_limit_minutes"] == 20
    assert repository.enable_calls == 0


@pytest.mark.asyncio
async def test_expired_access_code_is_replaced_only_by_explicit_generation(monkeypatch):
    fixed_now = datetime(2025, 6, 3, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    repository = FakeAccessCodeLifecycleRepository()
    service = LiveQuizSessionService(repository)

    with pytest.raises(HTTPException) as expired:
        await service.validate_access_code("KEEP42")
    assert expired.value.status_code == 410

    response = await service.generate_access_code(
        quiz_id="quiz-1",
        access_code_expires_at=fixed_now + timedelta(days=1),
        creator_id="creator-1",
        time_limit_minutes=30,
    )

    assert response["access_code"] != "KEEP42"
    assert repository.enable_calls == 1

    replacement = await service.validate_access_code(response["access_code"])
    assert replacement["quiz_id"] == "quiz-1"

    with pytest.raises(HTTPException) as old_code:
        await service.validate_access_code("KEEP42")
    assert old_code.value.status_code == 404


@pytest.mark.asyncio
async def test_creator_can_list_live_quizzes_with_stats(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(live_quiz_session_service, "_utc_now", lambda: fixed_now)

    service = LiveQuizSessionService(FakeCreatorLiveQuizzesRepository())

    rows = await service.list_creator_live_quizzes("creator-1")

    assert len(rows) == 1
    assert rows[0]["title"] == "Management Quiz"
    assert rows[0]["access_code"] == "LIVE01"
    assert rows[0]["access_code_expires_at"] == datetime(
        2025, 6, 2, tzinfo=timezone.utc
    )
    assert rows[0]["status"] == "in_progress"
    assert rows[0]["participant_count"] == 2
    assert rows[0]["completed_count"] == 1
    assert rows[0]["average_score"] == 2
