"""Authoritative server-side quiz grading.

Answers are graded against the stored quiz document, never against
correct answers supplied by the client. Correct answers are revealed
only in the grading response, after submission.
"""
from typing import Any, Optional

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


class SubmissionMismatchError(ValueError):
    """A submitted answer does not correspond to a question in the quiz."""


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

    Raises SubmissionMismatchError when a submitted question is not part of
    the stored quiz.
    """
    questions_by_text = {q["question"]: q for q in stored_questions}

    grading_payload = []
    for submitted in submitted_answers:
        stored = questions_by_text.get(submitted.get("question"))
        if stored is None:
            raise SubmissionMismatchError(
                "Submitted answers do not match this quiz's questions."
            )

        user_answer = submitted.get("user_answer")
        correct_answer = stored["correct_answer"]
        if quiz_type == "true-false":
            user_answer = _normalize_true_false(user_answer)
            correct_answer = _normalize_true_false(correct_answer)

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

    @staticmethod
    def _build_attempt_summary(graded_results: list[dict[str, Any]]) -> tuple[int, float]:
        total_questions = len(graded_results)
        score = sum(1 for result in graded_results if result.get("is_correct"))
        percentage = round((score / total_questions) * 100, 2) if total_questions else 0.0
        return score, percentage

    async def _store_attempt(
        self,
        *,
        user_id: str,
        quiz_id: str,
        graded_results: list[dict[str, Any]],
    ) -> None:
        score, percentage = self._build_attempt_summary(graded_results)
        await self.attempt_repository.insert_attempt(
            QuizAttemptDocumentV2(
                user_id=user_id,
                quiz_id=quiz_id,
                question_results=[
                    QuizAttemptQuestionResultV2(**graded_result)
                    for graded_result in graded_results
                ],
                score=score,
                percentage=percentage,
            )
        )

    async def _resolve_quiz(self, quiz_id: str) -> Optional[QuizDocumentV2]:
        quiz_doc = await self.quiz_repository.find_by_id(quiz_id)
        if not quiz_doc:
            saved_reference = await self.reference_repository.get_saved_quiz_by_public_id(quiz_id)
            if saved_reference:
                quiz_doc = await self.quiz_repository.find_by_id(saved_reference.quiz_id)
        return quiz_doc

    async def grade_submission(
        self,
        quiz_id: str,
        submitted_answers: list[dict[str, Any]],
        *,
        source: str = "mock",
        user_id: str | None = None,
    ) -> Optional[list[dict[str, Any]]]:
        """Returns graded results, or None when the quiz does not exist."""
        quiz_doc = await self._resolve_quiz(quiz_id)
        if quiz_doc is None:
            return None

        stored_questions = [
            {
                "question": question.question,
                "correct_answer": question.correct_answer,
            }
            for question in quiz_doc.questions
        ]
        graded_results = grade_against_stored_questions(
            stored_questions,
            submitted_answers,
            quiz_type=quiz_doc.quiz_type.value,
            source=source,
        )
        if user_id is not None:
            await self._store_attempt(
                user_id=user_id,
                quiz_id=str(quiz_doc.id),
                graded_results=graded_results,
            )
        return graded_results
