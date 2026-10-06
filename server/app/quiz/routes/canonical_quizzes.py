from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from server.app.core.dependencies import get_current_user_optional
from server.app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService
from server.app.share.services import can_access_quiz

router = APIRouter()


def _quiz_to_display_payload(quiz) -> dict[str, Any]:
    quiz_type = (
        quiz.quiz_type.value
        if hasattr(quiz.quiz_type, "value")
        else str(quiz.quiz_type)
    )
    visibility = (
        quiz.visibility.value
        if hasattr(quiz.visibility, "value")
        else str(quiz.visibility)
    )
    source = quiz.source.value if hasattr(quiz.source, "value") else str(quiz.source)
    return {
        "id": str(quiz.id),
        "quiz_id": str(quiz.id),
        "title": quiz.title,
        "description": quiz.description,
        "question_type": quiz_type,
        "quiz_type": quiz_type,
        "visibility": visibility,
        "source": source,
        "questions": [
            {
                "question": question.question,
                "options": question.options,
                "answer": question.correct_answer,
                "correct_answer": question.correct_answer,
                "question_type": quiz_type,
            }
            for question in quiz.questions
        ],
        "category": quiz.category,
        "category_slug": quiz.category_slug,
        "subcategory": quiz.subcategory,
        "subcategory_slug": quiz.subcategory_slug,
        "tags": quiz.tags,
        "classification": (
            quiz.classification.model_dump(mode="json") if quiz.classification else None
        ),
        "live_quiz_enabled": quiz.live_quiz_enabled,
        "time_limit_minutes": quiz.time_limit_minutes,
        "access_code": quiz.access_code,
        "access_code_expires_at": quiz.access_code_expires_at,
    }


@router.get("/quizzes/{quiz_id}", status_code=status.HTTP_200_OK)
async def get_canonical_quiz(
    quiz_id: str,
    current_user=Depends(get_current_user_optional),
):
    quiz = await CanonicalQuizWriteService().get_quiz_v2_by_id(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    current_user_id = str(current_user.id) if current_user else None
    if not can_access_quiz(quiz, current_user_id):
        quiz_status = (
            quiz.status.value if hasattr(quiz.status, "value") else str(quiz.status)
        )
        if quiz_status == "deleted":
            raise HTTPException(status_code=404, detail="Quiz not found")
        raise HTTPException(
            status_code=403, detail="You do not have access to this quiz"
        )

    return _quiz_to_display_payload(quiz)
