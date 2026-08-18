from datetime import datetime, timedelta

import pytest
from bson import ObjectId

from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.models.reference_models import QuizAttemptDocumentV2
from server.app.quiz.services.quiz_attempt_service import QuizAttemptService
from server.app.quiz.services.quiz_grading_service import QuizGradingService


class FakeQuizRepository:
    def __init__(self, quizzes: dict[str, QuizDocumentV2]):
        self.quizzes = quizzes

    async def find_by_id(self, quiz_id: str):
        return self.quizzes.get(quiz_id)

    async def find_many_by_ids(self, quiz_ids: list[str]):
        return [self.quizzes[quiz_id] for quiz_id in quiz_ids if quiz_id in self.quizzes]


class FakeReferenceRepository:
    async def get_saved_quiz_by_public_id(self, quiz_id: str):
        return None


class FakeAttemptRepository:
    def __init__(self, attempts: list[QuizAttemptDocumentV2] | None = None):
        self.attempts = attempts or []
        self.last_list_args: dict[str, object] | None = None

    async def insert_attempt(self, attempt: QuizAttemptDocumentV2):
        self.attempts.append(attempt)
        return attempt

    async def list_attempts_for_user(self, user_id: str, *, quiz_id: str | None = None, limit: int = 100):
        self.last_list_args = {"user_id": user_id, "quiz_id": quiz_id, "limit": limit}
        filtered = [
            attempt
            for attempt in self.attempts
            if attempt.user_id == user_id and (quiz_id is None or attempt.quiz_id == quiz_id)
        ]
        return sorted(filtered, key=lambda attempt: attempt.submitted_at, reverse=True)[:limit]

    async def get_attempt_by_id(self, attempt_id: str, *, user_id: str | None = None):
        for attempt in self.attempts:
            if str(attempt.id) == attempt_id and (user_id is None or attempt.user_id == user_id):
                return attempt
        return None

    async def soft_delete_attempt_by_id(self, attempt_id: str, *, user_id: str | None = None):
        for index, attempt in enumerate(self.attempts):
            if str(attempt.id) == attempt_id and (user_id is None or attempt.user_id == user_id):
                self.attempts.pop(index)
                return 1
        return 0


def build_quiz_document() -> QuizDocumentV2:
    quiz_id = ObjectId()
    return QuizDocumentV2(
        _id=quiz_id,
        title="Networking Basics",
        quiz_type="multichoice",
        source="manual",
        questions=[
            {
                "question": "What protocol serves web pages?",
                "options": ["HTTP", "SSH"],
                "correct_answer": "HTTP",
            },
            {
                "question": "Which port is commonly used for HTTPS?",
                "options": ["80", "443"],
                "correct_answer": "443",
            },
        ],
    )


@pytest.mark.asyncio
async def test_grade_submission_persists_attempt_for_authenticated_user():
    quiz = build_quiz_document()
    attempt_repository = FakeAttemptRepository()
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository({str(quiz.id): quiz}),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempt_repository,
    )

    results = await service.grade_submission(
        str(quiz.id),
        [
            {"question": "What protocol serves web pages?", "user_answer": "HTTP"},
            {"question": "Which port is commonly used for HTTPS?", "user_answer": "80"},
        ],
        source="mock",
        user_id="user-1",
    )

    assert len(results) == 2
    assert len(attempt_repository.attempts) == 1
    attempt = attempt_repository.attempts[0]
    assert attempt.user_id == "user-1"
    assert attempt.quiz_id == str(quiz.id)
    assert attempt.score == 1
    assert attempt.percentage == 50.0
    assert attempt.question_results[0].is_correct is True
    assert attempt.question_results[1].is_correct is False


@pytest.mark.asyncio
async def test_grade_submission_does_not_persist_attempt_for_anonymous_user():
    quiz = build_quiz_document()
    attempt_repository = FakeAttemptRepository()
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository({str(quiz.id): quiz}),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempt_repository,
    )

    await service.grade_submission(
        str(quiz.id),
        [{"question": "What protocol serves web pages?", "user_answer": "HTTP"}],
        source="mock",
        user_id=None,
    )

    assert attempt_repository.attempts == []


@pytest.mark.asyncio
async def test_list_attempts_returns_newest_first_and_passes_quiz_filter():
    quiz = build_quiz_document()
    quiz_two = QuizDocumentV2(
        _id=ObjectId(),
        title="Storage Basics",
        quiz_type="short-answer",
        source="manual",
        questions=[
            {
                "question": "What does SSD stand for?",
                "correct_answer": "Solid State Drive",
            }
        ],
    )
    attempt_repository = FakeAttemptRepository(
        attempts=[
            QuizAttemptDocumentV2(
                user_id="user-1",
                quiz_id=str(quiz.id),
                question_results=[
                    {
                        "question": "What protocol serves web pages?",
                        "user_answer": "SSH",
                        "correct_answer": "HTTP",
                        "question_type": "multichoice",
                        "is_correct": False,
                        "result": "Incorrect",
                    }
                ],
                score=0,
                percentage=0.0,
                submitted_at=datetime.utcnow() - timedelta(minutes=2),
            ),
            QuizAttemptDocumentV2(
                user_id="user-1",
                quiz_id=str(quiz_two.id),
                question_results=[
                    {
                        "question": "What does SSD stand for?",
                        "user_answer": "Solid State Drive",
                        "correct_answer": "Solid State Drive",
                        "question_type": "short-answer",
                        "accuracy_percentage": 100,
                        "is_correct": True,
                        "result": "Correct",
                    }
                ],
                score=1,
                percentage=100.0,
                submitted_at=datetime.utcnow(),
            ),
        ]
    )
    service = QuizAttemptService(
        quiz_repository=FakeQuizRepository(
            {
                str(quiz.id): quiz,
                str(quiz_two.id): quiz_two,
            }
        ),
        attempt_repository=attempt_repository,
    )

    payload = await service.list_attempts(user_id="user-1", quiz_id=str(quiz_two.id))

    assert attempt_repository.last_list_args == {
        "user_id": "user-1",
        "quiz_id": str(quiz_two.id),
        "limit": 100,
    }
    assert len(payload) == 1
    assert payload[0]["quiz_id"] == str(quiz_two.id)
    assert payload[0]["quiz_title"] == "Storage Basics"
    assert payload[0]["score"] == 1
    assert payload[0]["question_results"][0]["is_correct"] is True


@pytest.mark.asyncio
async def test_get_and_delete_attempt_use_user_scope():
    quiz = build_quiz_document()
    attempt = QuizAttemptDocumentV2(
        _id=ObjectId(),
        user_id="user-1",
        quiz_id=str(quiz.id),
        question_results=[
            {
                "question": "What protocol serves web pages?",
                "user_answer": "HTTP",
                "correct_answer": "HTTP",
                "question_type": "multichoice",
                "is_correct": True,
                "result": "Correct",
            }
        ],
        score=1,
        percentage=100.0,
    )
    attempt_repository = FakeAttemptRepository(attempts=[attempt])
    service = QuizAttemptService(
        quiz_repository=FakeQuizRepository({str(quiz.id): quiz}),
        attempt_repository=attempt_repository,
    )

    payload = await service.get_attempt(user_id="user-1", attempt_id=str(attempt.id))
    deleted = await service.delete_attempt(user_id="user-1", attempt_id=str(attempt.id))
    missing = await service.get_attempt(user_id="user-1", attempt_id=str(attempt.id))

    assert payload is not None
    assert payload["quiz_title"] == "Networking Basics"
    assert deleted is True
    assert missing is None
