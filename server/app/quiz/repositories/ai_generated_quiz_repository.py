import logging

from server.app.quiz.repositories.token_repository import get_user_token
from server.app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService
from server.app.quiz.services.category_taxonomy_service import (
    classify_quiz_taxonomy,
    normalize_quiz_type,
)


logger = logging.getLogger(__name__)
canonical_service = CanonicalQuizWriteService()


async def save_ai_generated_quiz(quiz_data: dict):
    try:
        quiz_type = normalize_quiz_type(quiz_data.get("question_type", "multichoice"))
        classification_token = quiz_data.get("token")
        if not classification_token and quiz_data.get("user_id"):
            classification_token = await get_user_token(quiz_data["user_id"])
        classification = await classify_quiz_taxonomy(
            quiz_type=quiz_type,
            title=quiz_data.get("profession") or "General Knowledge",
            profession=quiz_data.get("profession"),
            custom_instruction=quiz_data.get("custom_instruction"),
            questions=quiz_data.get("questions", []),
            token=classification_token,
            use_ai=True,
        )
        taxonomy_fields = classification.to_quiz_fields() if classification else {}
        quiz_document = canonical_service.build_quiz_document(
            title=quiz_data.get("profession") or "General Knowledge",
            description=quiz_data.get("custom_instruction"),
            quiz_type=quiz_type,
            owner_user_id=quiz_data.get("user_id"),
            source="ai",
            questions=quiz_data["questions"],
            tags=taxonomy_fields.get("tags"),
            category=taxonomy_fields.get("category"),
            category_slug=taxonomy_fields.get("category_slug"),
            subcategory=taxonomy_fields.get("subcategory"),
            subcategory_slug=taxonomy_fields.get("subcategory_slug"),
            persona_category=taxonomy_fields.get("persona_category"),
            classification=taxonomy_fields.get("classification"),
        )
        canonical_quiz = await canonical_service.find_or_create_quiz_v2_by_fingerprint(quiz_document)
        return {
            "message": "Quiz saved successfully",
            "quiz_id": str(canonical_quiz.id),
            "duplicate": False,
            "category": canonical_quiz.category,
            "category_slug": canonical_quiz.category_slug,
            "subcategory": canonical_quiz.subcategory,
            "subcategory_slug": canonical_quiz.subcategory_slug,
            "tags": canonical_quiz.tags,
            "classification": (
                canonical_quiz.classification.model_dump(mode="json")
                if canonical_quiz.classification
                else None
            ),
        }
    except Exception as exc:
        logger.error("Error saving quiz: %s", exc)
        raise
