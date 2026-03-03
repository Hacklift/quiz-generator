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
from pymongo.errors import PyMongoError
from bson.errors import InvalidId
from .quiz_write_service import (
    create_quiz_document,
    soft_delete_quiz_document,
    update_quiz_document,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



async def create_quiz(quizzes_collection: AsyncIOMotorCollection, quiz_data: NewQuizSchema) -> Optional[NewQuizResponse]:
    try:
        new_quiz_id, quiz_data_dict = await create_quiz_document(quizzes_collection, quiz_data)
        logger.info(f"New quiz created with ID: {new_quiz_id}")
        return NewQuizResponse(
            id=new_quiz_id,
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
        quiz = await quizzes_collection.find_one(
            {"_id": ObjectId(quiz_id), "is_deleted": {"$ne": True}},
            projection={"_id": 0},
        )
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
        updated_quiz = await update_quiz_document(quizzes_collection, quiz_id, update_data)

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
        modified_count = await soft_delete_quiz_document(quizzes_collection, quiz_id)
        if modified_count:
            return DeleteQuizResponse(
                message=f"Quiz with ID {quiz_id} deleted successfully",
                delete_count=modified_count
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
        quizzes_cursor = quizzes_collection.find({"is_deleted": {"$ne": True}})
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
