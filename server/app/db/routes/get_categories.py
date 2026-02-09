from fastapi import APIRouter, Query

from typing import List

from ....app.db.core.connection import quiz_categories_collection

from ....app.db.models.quiz_category_models import QuizQuestionModel


router = APIRouter()


@router.get("/categories", response_model=List[str])

async def get_categories():

    categories = await quiz_categories_collection.distinct("category")

    return categories


@router.get("/category/{category}/subcategories", response_model=List[str])

async def get_subcategories(category: str):

    subcategories = await quiz_categories_collection.distinct("subcategory", {"category": category})

    return subcategories


@router.get("/category/{category}/subcategory/{subcategory}/types", response_model=List[str])

async def get_quiz_types(category: str, subcategory: str):

    types = await quiz_categories_collection.distinct("question_type", {"category": category, "subcategory": subcategory})

    return types


@router.get(

    "/category/{category}/subcategory/{subcategory}/type/{question_type}",

    response_model=List[QuizQuestionModel],

)

async def get_quizzes_by_category_subcategory_type(

    category: str,

    subcategory: str,

    question_type: str,

    page: int = Query(1, ge=1),

    page_size: int = Query(5, ge=1, le=50),

):

    skip = (page - 1) * page_size

    docs = await quiz_categories_collection.find({

        "category": category,

        "subcategory": subcategory,

        "question_type": question_type,

    }).skip(skip).limit(page_size).to_list(length=page_size)


    questions = []

    for doc in docs:

        for q in doc.get("questions", []):

            q["subcategory"] = doc.get("subcategory")

            q["question_type"] = doc.get("question_type")

            questions.append(q)


    return questions

