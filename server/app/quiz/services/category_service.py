from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.services.category_taxonomy_service import (
    normalize_quiz_type,
    quiz_type_to_api_label,
    slugify,
)


class CategoryService:
    def __init__(self, repository: QuizV2Repository | None = None):
        self.repository = repository or QuizV2Repository(get_quizzes_v2_collection())

    async def list_categories(self, persona_category: str | None = None) -> list[str]:
        return await self.repository.list_category_values(persona_category)

    async def list_subcategories(self, category: str) -> list[str]:
        return await self.repository.list_subcategory_values(slugify(category))

    async def list_quiz_types(self, category: str, subcategory: str) -> list[str]:
        canonical_types = await self.repository.list_quiz_types_for_category(
            category_slug=slugify(category),
            subcategory_slug=slugify(subcategory),
        )
        return [quiz_type_to_api_label(quiz_type) for quiz_type in canonical_types]

    async def list_questions(
        self,
        *,
        category: str,
        subcategory: str,
        question_type: str,
        page: int,
        page_size: int,
    ) -> list[dict]:
        canonical_type = normalize_quiz_type(question_type)
        skip = (page - 1) * page_size
        questions = await self.repository.list_category_questions(
            category_slug=slugify(category),
            subcategory_slug=slugify(subcategory),
            quiz_type=canonical_type,
            skip=skip,
            limit=page_size,
        )
        for question in questions:
            question["question_type"] = quiz_type_to_api_label(question["question_type"])
            if question.get("options") is None:
                question.pop("options", None)
        return questions
