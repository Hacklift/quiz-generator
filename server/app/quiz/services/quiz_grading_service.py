"""Authoritative server-side quiz grading.

Answers are graded against the stored quiz document, never against
correct answers supplied by the client. Correct answers are revealed
only in the grading response, after submission.
"""
import logging
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Any, Optional

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


logger = logging.getLogger(__name__)


class SubmissionMismatchError(ValueError):
    """A submitted answer does not correspond to a question in the quiz."""


@dataclass(frozen=True)
class GradedQuizSubmission:
    results: list[dict[str, Any]]
    attempt_saved: bool | None = None


def _normalize_true_false(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"1", "true"}:
        return "true"
    if text in {"0", "false"}:
        return "false"
    return text


def grade_against_stored_questions(
    stored_questions: list[dict[str, Any]],
    submitted_answers: list[dict[str, Any]],
    *,
    quiz_type: str,
    source: str = "mock",
) -> list[dict[str, Any]]:
    """Grade submitted {question, user_answer} pairs against stored questions.

    Require exactly one answer per stored question for all callers. Repeated
    question text is matched in stored order rather than collapsing answer keys.
    """
    stored_question_counts = Counter(
        question["question"] for question in stored_questions
    )
    submitted_question_counts = Counter(
        submitted.get("question") for submitted in submitted_answers
    )
    if submitted_question_counts != stored_question_counts:
        raise SubmissionMismatchError(
            "Submitted answers do not match this quiz's questions."
        )

    questions_by_text = defaultdict(deque)
    for question in stored_questions:
        questions_by_text[question["question"]].append(question)

    grading_payload = []
    for submitted in submitted_answers:
        matching_questions = questions_by_text.get(submitted.get("question"))
        if not matching_questions:
            raise SubmissionMismatchError(
                "Submitted answers do not match this quiz's questions."
            )
        stored = matching_questions.popleft()

        user_answer = submitted.get("user_answer")
        correct_answer = stored["correct_answer"]
        if quiz_type == "true-false":
            user_answer = _normalize_true_false(user_answer)
            correct_answer = _normalize_true_false(correct_answer)
            if source == "ai":
                user_answer = {"true": 1, "false": 0}.get(user_answer, user_answer)
                correct_answer = {"true": 1, "false": 0}.get(correct_answer, correct_answer)

        grading_payload.append(
            {
                "question": stored["question"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "question_type": quiz_type,
            }
        )

    return grade_answers(grading_payload, source)


class QuizGradingService:
    def __init__(
        self,
        *,
        quiz_repository: Optional[QuizV2Repository] = None,
        reference_repository: Optional[ReferenceV2Repository] = None,
        attempt_repository: Optional[QuizAttemptV2Repository] = None,
        quiz_access: QuizPracticeAccess | None = None,
    ):
        self.quiz_repository = (
            quiz_repository
            if quiz_repository is not None
            else QuizV2Repository(get_quizzes_v2_collection())
        )
        self.reference_repository = (
            reference_repository
            if reference_repository is not None
            else ReferenceV2Repository(
                get_folders_v2_collection(),
                get_folder_items_v2_collection(),
                get_saved_quizzes_v2_collection(),
                get_quiz_history_v2_collection(),
            )
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
    ) -> Optional[QuizDocumentV2]:
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
