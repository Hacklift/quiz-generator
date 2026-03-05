from fastapi import APIRouter, HTTPException, Depends

from motor.motor_asyncio import AsyncIOMotorCollection

from ....app.db.core.connection import get_quizzes_collection

from ....app.db.crud.quiz_crud import (

    create_quiz,

    get_quiz,

    update_quiz,

    delete_quiz

    )

from ..schemas.quiz_schemas import (

    QuizSchema,

    NewQuizResponse,

    NewQuizSchema,

    UpdateQuiz,

    DeleteQuizResponse

    )


router = APIRouter()


@router.post("/test/create-quiz", response_model=NewQuizResponse)

async def create_new_quiz(

    quiz_data: NewQuizSchema,

    quizzes_collection: AsyncIOMotorCollection = Depends(get_quizzes_collection)

):

    new_quiz_response = await create_quiz(quizzes_collection, quiz_data)

    if not new_quiz_response:

        raise HTTPException(status_code=500, detail="Quiz creation failed")

    return new_quiz_response



@router.get("/test/get-quiz/{quiz_id}", response_model=QuizSchema)

async def get_quiz_by_id(

    quiz_id: str,

    quizzes_collection: AsyncIOMotorCollection = Depends(get_quizzes_collection)

):

    quiz = await get_quiz(quizzes_collection, quiz_id)

    if not quiz:

        raise HTTPException(status_code=404, detail="Quiz not found")

    return quiz



@router.put("/test/update-quiz/{quiz_id}", response_model=QuizSchema)

async def update_existing_quiz(

    quiz_id: str,

    quiz_update: UpdateQuiz,

    quizzes_collection: AsyncIOMotorCollection = Depends(get_quizzes_collection)

):

    updated_quiz_data = await update_quiz(quizzes_collection, quiz_id, quiz_update)

    if not updated_quiz_data:

        raise HTTPException(status_code=404, detail="Quiz not found or update failed")

    return updated_quiz_data



@router.delete("/test/delete-quiz/{quiz_id}", response_model=DeleteQuizResponse)

async def delete_existing_quiz(

    quiz_id: str,

    quizzes_collection: AsyncIOMotorCollection = Depends(get_quizzes_collection)

):

    result = await delete_quiz(quizzes_collection ,quiz_id)

    if result.delete_count == 0:

        raise HTTPException(status_code=404, detail=f"Quiz not found")

    return result

