from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_dict(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    if isinstance(payload, dict):
        return dict(payload)
    raise TypeError("Payload must be a dict or Pydantic model")


def _normalize_quiz_type(value: Optional[str]) -> str:
    if not value:
        return "multichoice"
    return value.strip().lower()


class CanonicalQuizQuestion(BaseModel):
    question: str
    options: Optional[List[str]] = None
    answer: str
    question_type: Optional[str] = None


class QuizGenerationMeta(BaseModel):
    profession: str
    difficulty_level: str
    num_questions: int
    audience_type: str
    custom_instruction: Optional[str] = None


class CanonicalQuizDocument(BaseModel):
    source: Literal["seed", "ai", "manual"]
    title: str
    description: Optional[str] = None
    quiz_type: str
    questions: List[CanonicalQuizQuestion]
    owner_id: Optional[str] = None
    generation: Optional[QuizGenerationMeta] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None


def adapt_question_to_canonical(question_payload: Any, *, fallback_quiz_type: Optional[str] = None) -> CanonicalQuizQuestion:
    question_data = _to_dict(question_payload)
    answer = question_data.get("answer", question_data.get("correct_answer"))
    if answer is None:
        raise ValueError("Question payload must contain either 'answer' or 'correct_answer'")

    question_type = question_data.get("question_type") or fallback_quiz_type

    return CanonicalQuizQuestion(
        question=question_data["question"],
        options=question_data.get("options"),
        answer=answer,
        question_type=_normalize_quiz_type(question_type) if question_type else None,
    )


def adapt_seed_quiz_to_canonical(seed_payload: Any) -> CanonicalQuizDocument:
    seed_data = _to_dict(seed_payload)
    quiz_type = _normalize_quiz_type(seed_data["quiz_type"])

    return CanonicalQuizDocument(
        source="seed",
        title=seed_data["title"],
        description=seed_data.get("description"),
        quiz_type=quiz_type,
        questions=[
            adapt_question_to_canonical(question, fallback_quiz_type=quiz_type)
            for question in seed_data.get("questions", [])
        ],
        owner_id=seed_data.get("owner_id"),
        created_at=seed_data.get("created_at") or _utcnow(),
        updated_at=seed_data.get("updated_at"),
    )


def adapt_ai_quiz_to_canonical(ai_payload: Any) -> CanonicalQuizDocument:
    ai_data = _to_dict(ai_payload)
    quiz_type = _normalize_quiz_type(ai_data["question_type"])
    profession = ai_data.get("profession", "General Knowledge")

    custom_instruction = ai_data.get("custom_instruction")
    description = ai_data.get("description")

    return CanonicalQuizDocument(
        source="ai",
        title=f"{profession} Quiz",
        description=description,
        quiz_type=quiz_type,
        questions=[
            adapt_question_to_canonical(question, fallback_quiz_type=quiz_type)
            for question in ai_data.get("questions", [])
        ],
        generation=QuizGenerationMeta(
            profession=profession,
            difficulty_level=ai_data.get("difficulty_level", "medium"),
            num_questions=ai_data.get("num_questions", len(ai_data.get("questions", []))),
            audience_type=ai_data.get("audience_type", "general"),
            custom_instruction=custom_instruction,
        ),
        created_at=ai_data.get("created_at") or _utcnow(),
        updated_at=ai_data.get("updated_at"),
    )
