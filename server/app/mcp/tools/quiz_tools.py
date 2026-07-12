from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.services.generation_policy import validate_generation_question_count
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService
from server.app.quiz.utils.questions import get_questions


def _validate_quiz_generate_request(
    *,
    profession: str,
    num_questions: int,
    question_type: str,
) -> None:
    missing_fields = []
    if not str(profession or "").strip():
        missing_fields.append("profession")
    if not str(question_type or "").strip():
        missing_fields.append("question_type")
    try:
        parsed_num_questions = int(num_questions)
    except (TypeError, ValueError):
        missing_fields.append("num_questions")
    else:
        if parsed_num_questions <= 0:
            missing_fields.append("num_questions")

    if missing_fields:
        raise ValueError(
            "quiz_generate requires profession/topic, question_type, and a positive num_questions value."
        )


def _history_questions(questions: list[dict], question_type: str) -> list[dict]:
    return [
        {
            "question": question.get("question"),
            "options": question.get("options"),
            "answer": question.get("answer") or question.get("correct_answer"),
            "question_type": question.get("question_type") or question_type,
        }
        for question in questions
    ]


async def quiz_generate(
    profession: str,
    num_questions: int,
    question_type: str,
    difficulty_level: str = "easy",
    audience_type: str = "students",
    custom_instruction: str | None = None,
    provider_token: str | None = None,
) -> dict:
    _validate_quiz_generate_request(
        profession=profession,
        num_questions=num_questions,
        question_type=question_type,
    )
    parsed_num_questions = validate_generation_question_count(num_questions)
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    request = QuizRequest(
        profession=profession,
        num_questions=parsed_num_questions,
        question_type=question_type,
        difficulty_level=difficulty_level,
        audience_type=audience_type,
        custom_instruction=custom_instruction,
        token=provider_token,
        live_quiz_enabled=False,
    )
    result = await get_questions(
        request,
        user_id=context.user_id,
    )
    questions = result.get("questions") or []
    history_id = None
    history_quiz_id = None

    if context.is_authenticated and questions:
        history_reference = await QuizUserLibraryService().create_quiz_history(
            {
                "user_id": context.user_id,
                "quiz_id": result.get("quiz_id"),
                "canonical_quiz_id": result.get("quiz_id"),
                "quiz_name": profession or f"{question_type} Quiz",
                "question_type": question_type,
                "num_questions": parsed_num_questions,
                "difficulty_level": difficulty_level,
                "profession": profession,
                "audience_type": audience_type,
                "custom_instruction": custom_instruction,
                "questions": _history_questions(questions, question_type),
            }
        )
        history_id = str(history_reference.id)
        history_quiz_id = history_reference.quiz_id

    return {
        **result,
        "quiz_id": result.get("quiz_id") or history_quiz_id,
        "history_id": history_id,
        "question_count": len(questions),
        "question_type": question_type,
        "title": profession or f"{question_type} Quiz",
    }
