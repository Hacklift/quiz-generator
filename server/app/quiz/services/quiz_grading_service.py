"""Authoritative deterministic grading for canonical quiz questions.

Answers are graded against stored quiz documents, never against correct
answers supplied by the client.
"""
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from server.app.organizations.models import OrganizationContext

from server.app.db.core.connection import (
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_attempts_v2_collection,
    get_quiz_history_v2_collection,
    get_quizzes_v2_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.models.reference_models import (
    QuizAttemptDocumentV2,
    QuizAttemptQuestionResultV2,
)
from server.app.quiz.repositories.v2.repositories.attempt_repository import QuizAttemptV2Repository
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.repositories.v2.repositories.reference_repository import ReferenceV2Repository
from server.app.quiz.utils.grading import grade_answers
from server.app.quiz.services.quiz_practice_access import QuizPracticeAccess

OBJECTIVE_TYPES = {"multichoice", "true-false", "short-answer", "matching"}

logger = logging.getLogger(__name__)


class SubmissionMismatchError(ValueError):
    """The submitted answers do not represent the complete canonical quiz."""


def _normalize_text(value: Any) -> str:
    return str(value if value is not None else "").strip().casefold()


@dataclass(frozen=True)
class GradedQuizSubmission:
    results: list[dict[str, Any]]
    attempt_saved: bool | None = None


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
    questions_by_text: dict[Any, deque[int]] = defaultdict(deque)
    for index, question in enumerate(stored_questions):
        questions_by_text[question.get("question")].append(index)
    for submitted in submitted_answers:
        index = submitted.get("question_index")
        if index is None:
            matching_indexes = questions_by_text.get(submitted.get("question"))
            index = matching_indexes.popleft() if matching_indexes else None
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
        quiz_access: QuizPracticeAccess | None = None,
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
        self.attempt_repository = (
            attempt_repository
            if attempt_repository is not None
            else QuizAttemptV2Repository(get_quiz_attempts_v2_collection())
        )
        self.quiz_access = quiz_access or QuizPracticeAccess()

    @staticmethod
    def _build_attempt_summary(graded_results: list[dict[str, Any]]) -> tuple[int, float]:
        total_questions = len(graded_results)
        score = sum(1 for result in graded_results if result.get("is_correct"))
        percentage = round((score / total_questions) * 100, 2) if total_questions else 0.0
        return score, percentage

    @staticmethod
    def _history_options(
        options: list[str] | None,
        *,
        question_type: str,
    ) -> list[str] | None:
        if options:
            return options
        if question_type == "true-false":
            return ["True", "False"]
        return None

    async def _store_attempt(
        self,
        *,
        user_id: str,
        organization_id: str,
        quiz_id: str,
        graded_results: list[dict[str, Any]],
        stored_questions: list[dict[str, Any]],
    ) -> None:
        score, percentage = self._build_attempt_summary(graded_results)
        options_by_text = defaultdict(deque)
        for question in stored_questions:
            options_by_text[question["question"]].append(question.get("options"))
        await self.attempt_repository.insert_attempt(
            QuizAttemptDocumentV2(
                user_id=user_id,
                organization_id=organization_id,
                created_by_user_id=user_id,
                quiz_id=quiz_id,
                question_results=[
                    QuizAttemptQuestionResultV2(
                        **graded_result,
                        options=self._history_options(
                            options_by_text[graded_result["question"]].popleft(),
                            question_type=str(
                                graded_result.get("question_type") or ""
                            ),
                        ),
                    )
                    for graded_result in graded_results
                ],
                score=score,
                percentage=percentage,
            )
        )

    async def _resolve_quiz(
        self, quiz_id: str, *, user_id: str | None, organization_id: str | None,
    ) -> QuizDocumentV2 | None:
        quizzes = await self.quiz_repository.find_attempt_source_quizzes(
            [quiz_id], organization_id=organization_id,
        )
        quiz_doc = next(iter(quizzes), None)
        if not quiz_doc and user_id is not None and organization_id:
            saved_reference = await self.reference_repository.get_saved_quiz_for_attempt(
                quiz_id, user_id=user_id, organization_id=organization_id,
            )
            if saved_reference:
                quizzes = await self.quiz_repository.find_attempt_source_quizzes(
                    [saved_reference.quiz_id], organization_id=organization_id,
                )
                quiz_doc = next(iter(quizzes), None)
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
        source: str = "mock",
        user_id: str | None = None,
        organization_id: str | None = None,
        organization: OrganizationContext | None = None,
    ) -> GradedQuizSubmission | None:
        """Return scores and independent persistence status, or None if missing."""
        if user_id is not None and not organization_id:
            raise HTTPException(status_code=409, detail="Organization context has not been provisioned")
        if organization is not None and (
            organization.principal.user_id != user_id
            or organization.organization_id != organization_id
        ):
            raise HTTPException(status_code=403, detail="Organization access denied")
        quiz_doc = await self._resolve_quiz(
            quiz_id, user_id=user_id, organization_id=organization_id,
        )
        if quiz_doc is None or quiz_doc.status.value == "deleted":
            return None
        await self.quiz_access.require_readable(quiz_doc, organization)

        stored_questions = [
            {
                "question": question.question,
                "correct_answer": question.correct_answer,
                "options": question.options,
                "question_type": quiz_doc.quiz_type.value,
            }
            for question in quiz_doc.questions
        ]
        graded_results = grade_against_stored_questions(
            stored_questions,
            submitted_answers,
            quiz_type=quiz_doc.quiz_type.value,
            source=source,
        )
        attempt_saved = None
        if user_id is not None:
            try:
                await self._store_attempt(
                    user_id=user_id,
                    organization_id=organization_id,
                    quiz_id=str(quiz_doc.id),
                    graded_results=graded_results,
                    stored_questions=stored_questions,
                )
                attempt_saved = True
            except Exception:
                logger.exception(
                    "Failed to persist quiz attempt for user_id=%s quiz_id=%s",
                    user_id,
                    str(quiz_doc.id),
                )
                attempt_saved = False
        return GradedQuizSubmission(results=graded_results, attempt_saved=attempt_saved)
