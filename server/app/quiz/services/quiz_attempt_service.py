from typing import Any

from server.app.db.core.connection import (
    get_quiz_attempts_v2_collection,
    get_quizzes_v2_collection,
)
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.repositories.attempt_repository import QuizAttemptV2Repository
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository


class QuizAttemptService:
    def __init__(
        self,
        *,
        quiz_repository: QuizV2Repository | None = None,
        attempt_repository: QuizAttemptV2Repository | None = None,
    ):
        self.quiz_repository = quiz_repository or QuizV2Repository(get_quizzes_v2_collection())
        self.attempt_repository = attempt_repository or QuizAttemptV2Repository(
            get_quiz_attempts_v2_collection()
        )

    @staticmethod
    def _attempt_payload(attempt, *, quiz_title: str | None) -> dict[str, Any]:
        return {
            "_id": str(attempt.id),
            "id": str(attempt.id),
            "quiz_id": attempt.quiz_id,
            "quiz_title": quiz_title,
            "score": attempt.score,
            "percentage": attempt.percentage,
            "total_questions": len(attempt.question_results),
            "submitted_at": attempt.submitted_at,
            "question_results": [
                {
                    "question": result.question,
                    "user_answer": result.user_answer,
                    "correct_answer": result.correct_answer,
                    "question_type": result.question_type,
                    "accuracy_percentage": result.accuracy_percentage,
                    "is_correct": result.is_correct,
                    "result": result.result,
                }
                for result in attempt.question_results
            ],
        }

    async def _get_quizzes_by_ids(self, quiz_ids: list[str]) -> dict[str, QuizDocumentV2]:
        quizzes = await self.quiz_repository.find_many_by_ids(quiz_ids)
        return {str(quiz.id): quiz for quiz in quizzes}

    async def list_attempts(
        self,
        *,
        user_id: str,
        quiz_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        attempts = await self.attempt_repository.list_attempts_for_user(
            user_id,
            quiz_id=quiz_id,
            limit=limit,
        )
        quizzes_by_id = await self._get_quizzes_by_ids([attempt.quiz_id for attempt in attempts])

        payloads: list[dict[str, Any]] = []
        for attempt in attempts:
            quiz = quizzes_by_id.get(attempt.quiz_id)
            payloads.append(self._attempt_payload(attempt, quiz_title=quiz.title if quiz else None))
        return payloads

    async def get_attempt(self, *, user_id: str, attempt_id: str) -> dict[str, Any] | None:
        attempt = await self.attempt_repository.get_attempt_by_id(
            attempt_id,
            user_id=user_id,
        )
        if attempt is None:
            return None
        quiz = await self.quiz_repository.find_by_id(attempt.quiz_id)
        return self._attempt_payload(attempt, quiz_title=quiz.title if quiz else None)

    async def delete_attempt(self, *, user_id: str, attempt_id: str) -> bool:
        return (
            await self.attempt_repository.soft_delete_attempt_by_id(
                attempt_id,
                user_id=user_id,
            )
        ) > 0
