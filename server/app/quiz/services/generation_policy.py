from fastapi import HTTPException, status

from server.app.core.config import settings


def validate_generation_question_count(num_questions: int) -> int:
    try:
        parsed = int(num_questions)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Number of questions must be a valid integer.",
        ) from exc

    if parsed < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Number of questions must be at least 1.",
        )

    if parsed > settings.QUIZ_GENERATION_MAX_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Quiz generation is limited to {settings.QUIZ_GENERATION_MAX_QUESTIONS} questions.",
        )

    return parsed
