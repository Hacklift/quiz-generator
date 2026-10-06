"""Authoritative deterministic grading for canonical quiz questions."""

from typing import Any

from server.app.db.core.connection import (
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_attempts_v2_collection,
    get_quiz_history_v2_collection,
    get_quizzes_v2_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.quiz.repositories.v2.models.attempt_models import (
    QuizAttemptDocumentV2,
    QuizAttemptQuestionResultV2,
)
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.repositories.attempt_repository import (
    QuizAttemptV2Repository,
)
from server.app.quiz.repositories.v2.repositories.quiz_repository import (
    QuizV2Repository,
)
from server.app.quiz.repositories.v2.repositories.reference_repository import (
    ReferenceV2Repository,
)
from server.app.quiz.utils.grading import grade_answers

OBJECTIVE_TYPES = {"multichoice", "true-false", "short-answer", "matching"}
GRADING_POLICY_VERSION = "objective-v1"


class SubmissionMismatchError(ValueError):
    """The submitted answers do not represent the complete canonical quiz."""


def _normalize_text(value: Any) -> str:
    return str(value if value is not None else "").strip().casefold()


def _normalize_true_false(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = _normalize_text(value)
    if text in {"1", "true"}:
        return "true"
    if text in {"0", "false"}:
        return "false"
    return text


def _normalize_matching(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, str] = {}
    for left, right in value.items():
        key, match = _normalize_text(left), _normalize_text(right)
        if not key or not match or key in normalized:
            return None
        normalized[key] = match
    return normalized


def _objective_is_correct(
    question_type: str, user_answer: Any, correct_answer: Any
) -> bool:
    if question_type == "true-false":
        return _normalize_true_false(user_answer) == _normalize_true_false(
            correct_answer
        )
    if question_type == "matching":
        submitted, authoritative = (
            _normalize_matching(user_answer),
            _normalize_matching(correct_answer),
        )
        return (
            submitted is not None
            and authoritative is not None
            and submitted == authoritative
        )
    return _normalize_text(user_answer) == _normalize_text(correct_answer)


def grade_against_stored_questions(
    stored_questions: list[dict[str, Any]],
    submitted_answers: list[dict[str, Any]],
    *,
    quiz_type: str,
    source: str = "mock",
) -> list[dict[str, Any]]:
    """Grade one complete submission against trusted canonical questions.

    ``source`` remains accepted for compatibility but affects only the existing
    non-objective/open-ended path.
    """
    answers_by_index: dict[int, Any] = {}
    questions_by_text = {
        question.get("question"): index
        for index, question in enumerate(stored_questions)
    }
    for submitted in submitted_answers:
        index = submitted.get("question_index")
        if index is None:
            index = questions_by_text.get(submitted.get("question"))
        if not isinstance(index, int) or index < 0 or index >= len(stored_questions):
            raise SubmissionMismatchError(
                "Submitted answers do not match this quiz's questions."
            )
        if index in answers_by_index:
            raise SubmissionMismatchError(
                "Each quiz question must be submitted exactly once."
            )
        answers_by_index[index] = submitted.get("user_answer")
    if set(answers_by_index) != set(range(len(stored_questions))):
        raise SubmissionMismatchError(
            "All quiz questions must be answered before submission."
        )

    results: list[dict[str, Any]] = []
    for index, stored in enumerate(stored_questions):
        question_type = str(stored.get("question_type") or quiz_type).strip().lower()
        user_answer, correct_answer = answers_by_index[index], stored["correct_answer"]
        if question_type in OBJECTIVE_TYPES:
            is_correct = _objective_is_correct(
                question_type, user_answer, correct_answer
            )
            if question_type == "true-false":
                user_answer = _normalize_true_false(user_answer)
                correct_answer = _normalize_true_false(correct_answer)
            results.append(
                {
                    "question_index": index,
                    "question": stored.get("question", ""),
                    "question_type": question_type,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "result": "Correct" if is_correct else "Incorrect",
                }
            )
            continue
        graded = grade_answers(
            [
                {
                    "question": stored.get("question", ""),
                    "question_type": question_type,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                }
            ],
            source,
        )
        if not graded:
            raise SubmissionMismatchError("The stored question cannot be graded.")
        graded[0]["question_index"] = index
        results.append(graded[0])
    return results


class QuizGradingService:
    def __init__(
        self,
        *,
        quiz_repository: QuizV2Repository | None = None,
        reference_repository: ReferenceV2Repository | None = None,
        attempt_repository: QuizAttemptV2Repository | None = None,
    ):
        self.quiz_repository = quiz_repository or QuizV2Repository(
            get_quizzes_v2_collection()
        )
        self.reference_repository = reference_repository or ReferenceV2Repository(
            get_folders_v2_collection(),
            get_folder_items_v2_collection(),
            get_saved_quizzes_v2_collection(),
            get_quiz_history_v2_collection(),
        )
        self.attempt_repository = attempt_repository or QuizAttemptV2Repository(
            get_quiz_attempts_v2_collection()
        )

    async def _resolve_quiz(self, quiz_id: str) -> QuizDocumentV2 | None:
        quiz_doc = await self.quiz_repository.find_by_id(quiz_id)
        if not quiz_doc:
            saved_reference = (
                await self.reference_repository.get_saved_quiz_by_public_id(quiz_id)
            )
            if saved_reference:
                quiz_doc = await self.quiz_repository.find_by_id(
                    saved_reference.quiz_id
                )
        return quiz_doc

    @staticmethod
    def grade_canonical_questions(
        questions: list[dict[str, Any]],
        submitted_answers: list[dict[str, Any]],
        *,
        quiz_type: str,
        source: str = "mock",
    ) -> dict[str, Any]:
        results = grade_against_stored_questions(
            questions, submitted_answers, quiz_type=quiz_type, source=source
        )
        total = len(questions)
        score = sum(1 for result in results if result.get("is_correct"))
        return {
            "score": score,
            "total_questions": total,
            "percentage": round((score / total) * 100, 2) if total else 0.0,
            "question_results": results,
        }

    async def grade_submission(
        self,
        quiz_id: str,
        submitted_answers: list[dict[str, Any]],
        *,
        user_id: str,
        source: str = "mock",
    ) -> dict[str, Any] | None:
        quiz_doc = await self._resolve_quiz(quiz_id)
        if quiz_doc is None:
            return None
        questions = [
            {
                "question": q.question,
                "correct_answer": q.correct_answer,
                "question_type": quiz_doc.quiz_type.value,
            }
            for q in quiz_doc.questions
        ]
        grading = self.grade_canonical_questions(
            questions,
            submitted_answers,
            quiz_type=quiz_doc.quiz_type.value,
            source=source,
        )
        attempt = QuizAttemptDocumentV2(
            user_id=user_id,
            quiz_id=str(quiz_doc.id),
            score=grading["score"],
            total_questions=grading["total_questions"],
            percentage=grading["percentage"],
            grading_policy_version=GRADING_POLICY_VERSION,
            question_results=[
                QuizAttemptQuestionResultV2(**result)
                for result in grading["question_results"]
            ],
        )
        stored = await self.attempt_repository.insert_attempt(attempt)
        return {
            "attempt_id": str(stored.id),
            "status": stored.status,
            **grading,
            "submitted_at": stored.submitted_at,
            "graded_at": stored.graded_at,
            "grading_policy_version": stored.grading_policy_version,
        }
