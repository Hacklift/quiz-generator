from fastapi import APIRouter, Query

from typing import List, Optional

from server.app.quiz.schemas.category_schemas import CategoryQuestionResponse
from server.app.quiz.services.category_service import CategoryService


router = APIRouter()


@router.get("/categories", response_model=List[str])

async def get_categories(persona_category: Optional[str] = Query(None, pattern="^(school|corporate)$")):

    return await CategoryService().list_categories(persona_category)


@router.get("/category/{category}/subcategories", response_model=List[str])

async def get_subcategories(category: str):

    return await CategoryService().list_subcategories(category)


@router.get("/category/{category}/subcategory/{subcategory}/types", response_model=List[str])

async def get_quiz_types(category: str, subcategory: str):

    return await CategoryService().list_quiz_types(category, subcategory)


@router.get(

    "/category/{category}/subcategory/{subcategory}/type/{question_type}",

    response_model=List[CategoryQuestionResponse],

)

async def get_quizzes_by_category_subcategory_type(

    category: str,

    subcategory: str,

    question_type: str,

    page: int = Query(1, ge=1),

    page_size: int = Query(5, ge=1, le=50),

):
    return await CategoryService().list_questions(
        category=category,
        subcategory=subcategory,
        question_type=question_type,
        page=page,
        page_size=page_size,
    )
