import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import server.app.quiz.services.live_session_service as live_quiz_session_service
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.questions import get_questions


@pytest.mark.asyncio
async def test_authenticated_get_questions_persists_fallback_quiz(monkeypatch):
    saved_payloads = []

    async def _raise_hf(*args, **kwargs):
        raise Exception("mocked HF down")

    async def _save(quiz_payload):
        saved_payloads.append(quiz_payload)
        return {"quiz_id": "canonical-quiz-1"}

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        _raise_hf,
    )
    monkeypatch.setattr(
        "server.app.quiz.utils.questions.save_ai_generated_quiz",
        _save,
    )

    result = await get_questions(
        QuizRequest(
            profession="Engineer",
            num_questions=2,
            question_type="multichoice",
            difficulty_level="medium",
            audience_type="students",
            custom_instruction="",
        ),
        user_id="user-1",
    )

    assert result["quiz_id"] == "canonical-quiz-1"
    assert saved_payloads
    assert saved_payloads[0]["user_id"] == "user-1"
    assert saved_payloads[0]["questions"]


class FakeLiveQuizRepository:
    def __init__(self):
        self.quiz = {
            "_id": "canonical-quiz-1",
            "title": "Generated Live Quiz",
            "owner_user_id": "user-1",
            "questions": [{"question": "Q1", "answer": "A"}],
        }

    async def get_quiz_by_id(self, quiz_id):
        return self.quiz

    async def access_code_exists(self, access_code):
        return False

    async def enable_live_quiz(self, **kwargs):
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
async def test_live_get_questions_creates_invitations_and_uses_frontend_base_url(monkeypatch):
    fixed_now = datetime(2025, 6, 1, 10, 30, tzinfo=timezone.utc)
    saved_payloads = []
    live_repository = FakeLiveQuizRepository()
    invitation_repository = FakeInvitationRepository()
    email_service = FakeEmailService()

    async def _generate(_payload):
        return {
            "questions": [
                {
                    "question": "Q1",
                    "options": ["A", "B"],
                    "answer": "A",
                }
            ]
        }

    async def _save(quiz_payload):
        saved_payloads.append(quiz_payload)
        return {"quiz_id": "canonical-quiz-1"}

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        _generate,
    )
    monkeypatch.setattr(
        "server.app.quiz.utils.questions.save_ai_generated_quiz",
        _save,
    )
    monkeypatch.setattr(
        "server.app.quiz.utils.questions.get_quizzes_v2_collection",
        lambda: object(),
    )
    monkeypatch.setattr(
        "server.app.quiz.utils.questions.get_live_quiz_sessions_collection",
        lambda: object(),
    )
    monkeypatch.setattr(
        "server.app.quiz.utils.questions.LiveQuizSessionRepository",
        lambda *_args, **_kwargs: live_repository,
    )
    monkeypatch.setattr(
        "server.app.quiz.services.live_session_service._utc_now",
        lambda: fixed_now,
    )
    monkeypatch.setattr(
        live_quiz_session_service.settings,
        "FRONTEND_BASE_URL",
        "https://trusted.example",
    )

    result = await get_questions(
        QuizRequest(
            profession="Engineer",
            num_questions=1,
            question_type="multichoice",
            difficulty_level="medium",
            audience_type="students",
            live_quiz_enabled=True,
            time_limit_minutes=15,
            access_code_expires_at=fixed_now + timedelta(days=1),
            participant_access_mode="restricted",
            invited_emails=["ADA@example.com"],
            send_email_invitations=True,
        ),
        user_id="user-1",
        invitation_repository=invitation_repository,
        email_service=email_service,
    )

    assert result["quiz_id"] == "canonical-quiz-1"
    assert result["invited_emails"] == ["ada@example.com"]
    assert result["invitations_created"] == 1
    assert result["invitations_queued"] == 1
    assert result["invitations_delivered"] == 0
    assert invitation_repository.invitations[0]["email"] == "ada@example.com"
    assert invitation_repository.deliveries[0]["status"] == "queued"
    body = email_service.sent[0]["template_vars"]["body"]
    assert "https://trusted.example/quiz-access/" in body
    assert "https://attacker.example" not in body
