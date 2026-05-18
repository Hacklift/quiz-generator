from pydantic import ValidationError

from ....app.db.models.saved_quiz_model import QuizQuestionModel
from ....app.db.services.quiz_dual_write_service import QuizDualWriteService


dual_write_service = QuizDualWriteService()
collection = None


async def save_quiz(
    user_id: str,
    title: str,
    question_type: str,
    questions: list,
    quiz_id: str | None = None,
):
    try:
        parsed_questions = []
        for question in questions:
            if isinstance(question, dict):
                question_payload = {
                    **question,
                    "question_type": question.get("question_type") or question_type,
                }
                parsed_questions.append(QuizQuestionModel(**question_payload))
            else:
                if not getattr(question, "question_type", None):
                    question.question_type = question_type
                parsed_questions.append(question)

        return await dual_write_service.create_saved_quiz_v2(
            user_id=user_id,
            title=title,
            question_type=question_type,
            questions=parsed_questions,
            quiz_id=quiz_id,
        )
    except ValidationError as exc:
        raise Exception(f"Validation error: {exc}") from exc


async def delete_saved_quiz(quiz_id: str, user_id: str):
    return await dual_write_service.delete_saved_quiz_v2(
        saved_quiz_id=quiz_id,
        user_id=user_id,
    )
