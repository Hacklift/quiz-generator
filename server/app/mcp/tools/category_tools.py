from server.app.quiz.services.category_service import CategoryService


async def category_list() -> list[str]:
    return await CategoryService().list_categories()


async def category_list_subcategories(category: str) -> list[str]:
    return await CategoryService().list_subcategories(category)


async def category_list_quiz_types(category: str, subcategory: str) -> list[str]:
    return await CategoryService().list_quiz_types(category, subcategory)


async def category_browse_questions(
    category: str,
    subcategory: str,
    question_type: str,
    page: int = 1,
    page_size: int = 5,
) -> list[dict]:
    return await CategoryService().list_questions(
        category=category,
        subcategory=subcategory,
        question_type=question_type,
        page=page,
        page_size=page_size,
    )
