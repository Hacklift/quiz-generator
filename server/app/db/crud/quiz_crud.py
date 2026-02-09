from motor.motor_asyncio import AsyncIOMotorCollection

from bson import ObjectId

from ..schemas.quiz_schemas import (

    QuizSchema,

    NewQuizResponse,

    NewQuizSchema,

    UpdateQuiz,

    DeleteQuizResponse

    )

import logging

from typing import Optional, List

from pymongo import ReturnDocument

from pymongo.errors import PyMongoError

from bson.errors import InvalidId

from datetime import datetime, timezone


logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)




async def create_quiz(quizzes_collection: AsyncIOMotorCollection, quiz_data: NewQuizSchema) -> Optional[NewQuizResponse]:

    try:

        quiz_data_dict = quiz_data.model_dump()

        new_quiz = await quizzes_collection.insert_one(quiz_data_dict)

        logger.info(f"New quiz created with ID: {new_quiz.inserted_id}")

        return NewQuizResponse(

            id=str(new_quiz.inserted_id),

            title=quiz_data_dict["title"],

            description=quiz_data_dict["description"]

        )

    except PyMongoError as e:

        logger.error(f"Error occurred while creating quiz: {e}")

    except ValueError as e:

        logger.error(f"Invalid data: {e}")

    return None



async def get_quiz(quizzes_collection: AsyncIOMotorCollection, quiz_id: str) -> Optional[QuizSchema]:

    try:

        quiz = await quizzes_collection.find_one({"_id": ObjectId(quiz_id)}, projection={"_id": 0})

        if quiz:

            return QuizSchema(**quiz, id=quiz_id)

        return None

    except InvalidId as e:

        logger.error(f"Invalid quiz ID: {e}")

    except PyMongoError as e:

        logger.error(f"Error retrieving quiz: {e}")

    return None



async def update_quiz(quizzes_collection: AsyncIOMotorCollection, quiz_id: str, update_data: UpdateQuiz) -> Optional[QuizSchema]:

    try:

        update_data_dict = update_data.model_dump(exclude_unset=True)

        update_data_dict["updated_at"] = datetime.now(timezone.utc)


        updated_quiz = await quizzes_collection.find_one_and_update(

            {"_id": ObjectId(quiz_id)},

            {"$set": update_data_dict},

            return_document=ReturnDocument.AFTER

        )


        if updated_quiz:

            return QuizSchema(**updated_quiz, id=str(updated_quiz["_id"]))


    except InvalidId as e:

        logger.error(f"Invalid quiz ID: {e}")

    except ValueError as e:

        logger.error(f"Invalid data: {e}")

    except PyMongoError as e:

        logger.error(f"Error occurred while updating quiz: {e}")

    return None



async def delete_quiz(quizzes_collection: AsyncIOMotorCollection, quiz_id: str) -> DeleteQuizResponse:

    try:

        result = await quizzes_collection.delete_one({"_id": ObjectId(quiz_id)})

        if result.deleted_count:

            return DeleteQuizResponse(

                message=f"Quiz with ID {quiz_id} deleted successfully",

                delete_count=result.deleted_count

            )

        return DeleteQuizResponse(

            message=f"No quiz found with ID {quiz_id}",

            delete_count=0

        )

    except InvalidId as e:

        logger.error(f"Invalid quiz ID: {e}")

    except PyMongoError as e:

        logger.error(f"Error deleting quiz: {e}")

    return DeleteQuizResponse(message="An error occurred while deleting the quiz", delete_count=0)



async def list_quizzes(quizzes_collection: AsyncIOMotorCollection) -> List[QuizSchema]:

    try:

        quizzes_cursor = quizzes_collection.find({})

        quizzes = await quizzes_cursor.to_list(length=8)


        return [

        QuizSchema(

        id=str(quiz["_id"]),

        title=quiz["title"],

        description=quiz["description"],

        quiz_type=quiz["quiz_type"],

        owner_id=quiz["owner_id"],

        created_at=quiz["created_at"],

        updated_at=quiz["updated_at"],

        questions=quiz["questions"]

        )

        for quiz in quizzes

        ]


    except PyMongoError as e:

        logger.error(f"Database error while listing quizzes: {e}")

    return []

