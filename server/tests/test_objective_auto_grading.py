from datetime import datetime

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.routes import grading as grading_route
from server.app.quiz.routes.grading import GradeQuizRequest
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.services.quiz_grading_service import (
    QuizGradingService,
    SubmissionMismatchError,
    grade_against_stored_questions,
)


def grade_one(question_type, correct_answer, user_answer, *, source="mock"):
    return grade_against_stored_questions(
        [
            {
                "question": "Q",
                "question_type": question_type,
                "correct_answer": correct_answer,
            }
        ],
        [{"question_index": 0, "user_answer": user_answer}],
        quiz_type=question_type,
        source=source,
    )[0]


def test_mcq_uses_authoritative_answer():
    assert grade_one("multichoice", "Paris", " paris ")["is_correct"] is True
    assert grade_one("multichoice", "Paris", "London")["is_correct"] is False


@pytest.mark.parametrize("submitted", [True, 1, "TRUE", " true "])
def test_true_false_normalizes_supported_values_and_ignores_source(submitted):
    assert (
        grade_one("true-false", "true", submitted, source="mock")["is_correct"] is True
    )
    assert grade_one("true-false", "true", submitted, source="ai")["is_correct"] is True
    assert (
        grade_one("true-false", "false", submitted, source="ai")["is_correct"] is False
    )


def test_short_answer_is_normalized_exact_match_not_fuzzy():
    assert (
        grade_one("short-answer", "Solid State Drive", "  solid state drive  ")[
            "is_correct"
        ]
        is True
    )
    assert (
        grade_one("short-answer", "Solid State Drive", "Solid State Drives")[
            "is_correct"
        ]
        is False
    )
    assert (
        grade_one(
            "short-answer", "Solid State Drive", "Solid State Drives", source="ai"
        )["is_correct"]
        is False
    )


def test_open_ended_keeps_separate_fuzzy_semantics():
    result = grade_one(
        "open-ended",
        "plants use sunlight to make food",
        "plants use sunlight to make food",
    )
    assert result["is_correct"] is True
    assert "accuracy_percentage" in result


def test_matching_is_complete_order_independent_and_authoritative():
    correct = {"France": "Paris", "Italy": "Rome"}
    assert (
        grade_one("matching", correct, {"italy": " rome ", "FRANCE": "PARIS"})[
            "is_correct"
        ]
        is True
    )
    assert (
        grade_one("matching", correct, {"France": "Rome", "Italy": "Paris"})[
            "is_correct"
        ]
        is False
    )
    assert grade_one("matching", correct, {"France": "Paris"})["is_correct"] is False
    assert (
        grade_one("matching", correct, {**correct, "Spain": "Madrid"})["is_correct"]
        is False
    )


def test_submission_integrity_uses_authoritative_question_set():
    questions = [
        {"question": "Q1", "correct_answer": "A"},
        {"question": "Q2", "correct_answer": "B"},
    ]
    with pytest.raises(SubmissionMismatchError):
        grade_against_stored_questions(
            questions,
            [{"question_index": 0, "user_answer": "A"}],
            quiz_type="multichoice",
        )
    with pytest.raises(SubmissionMismatchError):
        grade_against_stored_questions(
            questions,
            [
                {"question_index": 0, "user_answer": "A"},
                {"question_index": 0, "user_answer": "A"},
            ],
            quiz_type="multichoice",
        )
    with pytest.raises(SubmissionMismatchError):
        grade_against_stored_questions(
            questions,
            [
                {"question_index": 0, "user_answer": "A"},
                {"question_index": 9, "user_answer": "B"},
            ],
            quiz_type="multichoice",
        )


def test_request_forbids_client_grading_fields():
    with pytest.raises(ValidationError):
        GradeQuizRequest.model_validate(
            {
                "answers": [
                    {
                        "question_index": 0,
                        "user_answer": "wrong",
                        "correct_answer": "wrong",
                        "is_correct": True,
                        "score": 100,
                        "percentage": 100,
                        "question_type": "multichoice",
                        "grading_source": "ai",
                    }
                ]
            }
        )


class FakeQuizRepository:
    def __init__(self, quiz):
        self.quiz = quiz

    async def find_by_id(self, quiz_id):
        return self.quiz


class FakeReferenceRepository:
    async def get_saved_quiz_by_public_id(self, quiz_id):
        return None


class FakeAttemptRepository:
    def __init__(self, *, fail=False):
        self.attempts = []
        self.fail = fail

    async def insert_attempt(self, attempt):
        if self.fail:
            raise RuntimeError("database unavailable")
        self.attempts.append(attempt)
        return attempt


def make_quiz(
    *,
    owner_user_id=None,
    visibility="private",
    status="active",
):
    return QuizDocumentV2(
        _id=ObjectId(),
        title="Objective quiz",
        quiz_type="multichoice",
        source="manual",
        owner_user_id=owner_user_id,
        visibility=visibility,
        status=status,
        questions=[
            {"question": "Q1", "correct_answer": "A", "options": ["A", "B"]},
            {"question": "Q2", "correct_answer": "B", "options": ["A", "B"]},
        ],
    )


def complete_answers():
    return [
        {"question_index": 0, "user_answer": "A"},
        {"question_index": 1, "user_answer": "B"},
    ]


@pytest.mark.asyncio
async def test_private_quiz_owner_can_grade_and_persist_attempt():
    quiz, attempts = make_quiz(owner_user_id="user-a"), FakeAttemptRepository()
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository(quiz),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )

    response = await service.grade_submission(
        str(quiz.id), complete_answers(), user_id="user-a"
    )

    assert response is not None
    assert response["score"] == 2
    assert len(attempts.attempts) == 1


@pytest.mark.asyncio
async def test_private_quiz_non_owner_gets_no_result_or_correct_answers_and_no_attempt():
    quiz, attempts = make_quiz(owner_user_id="user-a"), FakeAttemptRepository()
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository(quiz),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )

    response = await service.grade_submission(
        str(quiz.id), complete_answers(), user_id="user-b"
    )

    assert response is None
    assert attempts.attempts == []


@pytest.mark.asyncio
@pytest.mark.parametrize("visibility", ["public", "unlisted"])
async def test_non_owner_can_grade_shareable_quiz(visibility):
    quiz, attempts = (
        make_quiz(owner_user_id="user-a", visibility=visibility),
        FakeAttemptRepository(),
    )
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository(quiz),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )

    response = await service.grade_submission(
        str(quiz.id), complete_answers(), user_id="user-b"
    )

    assert response is not None
    assert response["question_results"][0]["correct_answer"] == "A"
    assert len(attempts.attempts) == 1


@pytest.mark.asyncio
async def test_deleted_quiz_cannot_be_graded_even_by_owner():
    quiz, attempts = (
        make_quiz(owner_user_id="user-a", status="deleted"),
        FakeAttemptRepository(),
    )
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository(quiz),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )

    assert (
        await service.grade_submission(
            str(quiz.id), complete_answers(), user_id="user-a"
        )
        is None
    )
    assert attempts.attempts == []


@pytest.mark.asyncio
async def test_grading_route_maps_hidden_quiz_to_404(monkeypatch):
    class HiddenQuizService:
        async def grade_submission(self, *args, **kwargs):
            return None

    monkeypatch.setattr(grading_route, "QuizGradingService", HiddenQuizService)
    payload = GradeQuizRequest.model_validate({"answers": complete_answers()})
    current_user = type("CurrentUser", (), {"id": "user-b"})()

    with pytest.raises(HTTPException) as exc_info:
        await grading_route.grade_quiz_submission.__wrapped__(
            request=None,
            response=None,
            quiz_id="private-quiz-id",
            payload=payload,
            source="mock",
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Quiz not found"


@pytest.mark.asyncio
async def test_grading_route_does_not_expose_internal_exception_text(monkeypatch):
    class FailingService:
        async def grade_submission(self, *args, **kwargs):
            raise RuntimeError("internal database credentials")

    monkeypatch.setattr(grading_route, "QuizGradingService", FailingService)
    payload = GradeQuizRequest.model_validate({"answers": complete_answers()})
    current_user = type("CurrentUser", (), {"id": "user-a"})()

    with pytest.raises(HTTPException) as exc_info:
        await grading_route.grade_quiz_submission.__wrapped__(
            request=None,
            response=None,
            quiz_id="quiz-id",
            payload=payload,
            source="mock",
            current_user=current_user,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Could not grade quiz"
    assert "credentials" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticated_submission_persists_complete_attempt_before_response():
    quiz, attempts = make_quiz(), FakeAttemptRepository()
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository(quiz),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )
    response = await service.grade_submission(
        str(quiz.id),
        [
            {"question_index": 0, "user_answer": "A"},
            {"question_index": 1, "user_answer": "A"},
        ],
        user_id="learner-1",
    )
    assert len(attempts.attempts) == 1
    attempt = attempts.attempts[0]
    assert response["attempt_id"] == str(attempt.id)
    assert (attempt.user_id, attempt.quiz_id, attempt.status) == (
        "learner-1",
        str(quiz.id),
        "completed",
    )
    assert (attempt.score, attempt.total_questions, attempt.percentage) == (1, 2, 50.0)
    assert len(attempt.question_results) == 2
    assert attempt.question_results[0].correct_answer == "A"
    assert all(
        isinstance(value, datetime)
        for value in (
            attempt.submitted_at,
            attempt.graded_at,
            attempt.created_at,
            attempt.updated_at,
        )
    )


@pytest.mark.asyncio
async def test_persistence_failure_does_not_return_success():
    quiz = make_quiz()
    service = QuizGradingService(
        quiz_repository=FakeQuizRepository(quiz),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=FakeAttemptRepository(fail=True),
    )
    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.grade_submission(
            str(quiz.id),
            [
                {"question_index": 0, "user_answer": "A"},
                {"question_index": 1, "user_answer": "B"},
            ],
            user_id="learner-1",
        )


def test_live_and_parent_practice_use_shared_objective_semantics(monkeypatch):
    calls = []
    original = QuizGradingService.grade_canonical_questions

    def spy(questions, answers, **kwargs):
        calls.append((questions, answers))
        return original(questions, answers, **kwargs)

    monkeypatch.setattr(
        QuizGradingService, "grade_canonical_questions", staticmethod(spy)
    )
    service = LiveQuizSessionService(object())
    quiz = {
        "quiz_type": "multichoice",
        "questions": [
            {"question": "MCQ", "question_type": "multichoice", "correct_answer": "A"},
            {"question": "TF", "question_type": "true-false", "correct_answer": "true"},
            {
                "question": "Short",
                "question_type": "short-answer",
                "correct_answer": "H2O",
            },
            {
                "question": "Match",
                "question_type": "matching",
                "correct_answer": {"H": "Hydrogen"},
            },
        ],
    }
    session = {
        "answers": [
            {"question_index": 0, "selected_answer": "a"},
            {"question_index": 1, "selected_answer": 1},
            {"question_index": 2, "selected_answer": " h2o "},
            {"question_index": 3, "selected_answer": {"h": "hydrogen"}},
        ]
    }
    result = service._grade_session(session, quiz)
    assert len(calls) == 1
    assert result["score"] == 4
    assert result["percentage"] == 100
    assert len(result["graded_answers"]) == 4
