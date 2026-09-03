import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import server.app.quiz.services.live_session_service as live_quiz_session_service
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService
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


@pytest.mark.asyncio
async def test_parent_generation_can_disable_unrelated_fallback(monkeypatch):
    async def _raise_hf(*args, **kwargs):
        raise Exception("mocked HF down")

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        _raise_hf,
    )

    with pytest.raises(Exception) as error:
        await get_questions(
            QuizRequest(
                profession="Multiplication tables",
                num_questions=10,
                question_type="multichoice",
                difficulty_level="easy",
                audience_type="children ages 7–9",
                allow_fallback=False,
            ),
            user_id="parent-1",
        )

    assert getattr(error.value, "status_code", None) == 503


class FingerprintRepository:
    OWNER_SCOPE_UNSET = object()

    def __init__(self):
        self.documents = {}

    async def find_by_content_fingerprint(
        self, content_fingerprint, owner_user_id=OWNER_SCOPE_UNSET
    ):
        if owner_user_id is not self.OWNER_SCOPE_UNSET:
            return self.documents.get((content_fingerprint, owner_user_id))
        return next(
            (
                quiz
                for (fingerprint, _owner_id), quiz in self.documents.items()
                if fingerprint == content_fingerprint
            ),
            None,
        )

    async def insert_quiz(self, quiz):
        self.documents[(quiz.content_fingerprint, quiz.owner_user_id)] = quiz
        return quiz

    async def find_or_create_by_fingerprint(self, quiz):
        existing = await self.find_by_content_fingerprint(
            quiz.content_fingerprint,
            quiz.owner_user_id,
        )
        return existing or await self.insert_quiz(quiz)


class QueryRecordingCollection:
    def __init__(self):
        self.queries = []

    async def find_one(self, query):
        self.queries.append(query)
        return None


@pytest.mark.asyncio
async def test_fingerprint_lookup_only_adds_owner_scope_when_requested():
    collection = QueryRecordingCollection()
    repository = QuizV2Repository(collection)

    await repository.find_by_content_fingerprint("legacy-fingerprint")
    await repository.find_by_content_fingerprint("owned-fingerprint", "parent-1")
    await repository.find_by_content_fingerprint("ownerless-fingerprint", None)

    assert collection.queries == [
        {"content_fingerprint": "legacy-fingerprint"},
        {
            "content_fingerprint": "owned-fingerprint",
            "owner_user_id": "parent-1",
        },
        {"content_fingerprint": "ownerless-fingerprint", "owner_user_id": None},
    ]


@pytest.mark.asyncio
async def test_identical_generated_content_is_scoped_to_owner():
    repository = FingerprintRepository()
    service = CanonicalQuizWriteService(repository)
    common = {
        "title": "Multiplication Tables",
        "quiz_type": "multichoice",
        "source": "ai",
        "questions": [
            {
                "question": "What is 7 x 8?",
                "options": ["54", "56", "63", "64"],
                "answer": "56",
            }
        ],
    }

    first = await service.find_or_create_quiz_v2_by_fingerprint(
        service.build_quiz_document(**common, owner_user_id="parent-1")
    )
    second = await service.find_or_create_quiz_v2_by_fingerprint(
        service.build_quiz_document(**common, owner_user_id="parent-2")
    )
    first_again = await service.find_or_create_quiz_v2_by_fingerprint(
        service.build_quiz_document(**common, owner_user_id="parent-1")
    )

    assert first.owner_user_id == "parent-1"
    assert second.owner_user_id == "parent-2"
    assert first is not second
    assert first_again is not second
    assert first.content_fingerprint == second.content_fingerprint
    assert first_again is first
    assert len(repository.documents) == 2


@pytest.mark.asyncio
async def test_content_fingerprint_remains_compatible_with_content_only_algorithm():
    service = CanonicalQuizWriteService(FingerprintRepository())
    common = {
        "title": "Compatibility Quiz",
        "description": "Existing fingerprint format",
        "quiz_type": "multichoice",
        "questions": [
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4"],
                "answer": "4",
            }
        ],
    }
    document = service.build_quiz_document(**common, owner_user_id="parent-1")
    expected_payload = {
        "title": "Compatibility Quiz",
        "description": "Existing fingerprint format",
        "quiz_type": "multichoice",
        "questions": [
            {
                "question": "What is 2 + 2?",
                "options": ["3", "4"],
                "correct_answer": "4",
            }
        ],
    }
    expected = hashlib.sha256(
        json.dumps(expected_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    assert document.content_fingerprint == expected


@pytest.mark.asyncio
async def test_ownerless_content_still_deduplicates():
    repository = FingerprintRepository()
    service = CanonicalQuizWriteService(repository)
    common = {
        "title": "Legacy Seed Quiz",
        "quiz_type": "multichoice",
        "source": "legacy",
        "questions": [
            {"question": "Seed question", "options": ["A", "B"], "answer": "A"}
        ],
    }

    first = await service.find_or_create_quiz_v2_by_fingerprint(
        service.build_quiz_document(**common)
    )
    second = await service.find_or_create_quiz_v2_by_fingerprint(
        service.build_quiz_document(**common, owner_user_id=None)
    )

    assert second is first
    assert first.owner_user_id is None
    assert len(repository.documents) == 1


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
