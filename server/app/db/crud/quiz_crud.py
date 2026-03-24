from datetime import datetime, timezone
import logging
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from ..schemas.quiz_schemas import (
    DeleteQuizResponse,
    NewQuizResponse,
    NewQuizSchema,
    QuizSchema,
    UpdateQuiz,
)
from ..services.quiz_dual_write_service import QuizDualWriteService


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

dual_write_service = QuizDualWriteService()


async def create_quiz(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_data: NewQuizSchema,
) -> Optional[NewQuizResponse]:
    try:
        quiz_data_dict = quiz_data.model_dump()
        new_quiz = await quizzes_collection.insert_one(quiz_data_dict)

        try:
            mirrored = await dual_write_service.mirror_legacy_manual_quiz(
                str(new_quiz.inserted_id),
                {**quiz_data_dict, "_id": new_quiz.inserted_id},
            )
            if mirrored:
                await quizzes_collection.update_one(
                    {"_id": new_quiz.inserted_id},
                    {"$set": {"canonical_quiz_id": str(mirrored.id)}},
                )
        except Exception as exc:
            logger.exception(
                "Manual quiz dual-write failed after legacy insert for quiz_id=%s: %s",
                new_quiz.inserted_id,
                exc,
            )

        logger.info("New quiz created with ID: %s", new_quiz.inserted_id)
        return NewQuizResponse(
            id=str(new_quiz.inserted_id),
            title=quiz_data_dict["title"],
            description=quiz_data_dict["description"],
        )
    except PyMongoError as exc:
        logger.error("Error occurred while creating quiz: %s", exc)
    except ValueError as exc:
        logger.error("Invalid data: %s", exc)
    return None


async def get_quiz(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_id: str,
) -> Optional[QuizSchema]:
    try:
        quiz = await quizzes_collection.find_one(
            {"_id": ObjectId(quiz_id)},
            projection={"_id": 0},
        )
        if quiz:
            return QuizSchema(**quiz, id=quiz_id)
        return None
    except InvalidId as exc:
        logger.error("Invalid quiz ID: %s", exc)
    except PyMongoError as exc:
        logger.error("Error retrieving quiz: %s", exc)
    return None


async def update_quiz(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_id: str,
    update_data: UpdateQuiz,
) -> Optional[QuizSchema]:
    try:
        update_data_dict = update_data.model_dump(exclude_unset=True)
        update_data_dict["updated_at"] = datetime.now(timezone.utc)

        updated_quiz = await quizzes_collection.find_one_and_update(
            {"_id": ObjectId(quiz_id)},
            {"$set": update_data_dict},
            return_document=ReturnDocument.AFTER,
        )
        if updated_quiz:
            try:
                await dual_write_service.mirror_legacy_manual_quiz(
                    str(updated_quiz["_id"]),
                    updated_quiz,
                )
            except Exception as exc:
                logger.exception(
                    "Manual quiz dual-write failed after legacy update for quiz_id=%s: %s",
                    updated_quiz["_id"],
                    exc,
                )
            return QuizSchema(**updated_quiz, id=str(updated_quiz["_id"]))
    except InvalidId as exc:
        logger.error("Invalid quiz ID: %s", exc)
    except ValueError as exc:
        logger.error("Invalid data: %s", exc)
    except PyMongoError as exc:
        logger.error("Error occurred while updating quiz: %s", exc)
    return None


async def delete_quiz(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_id: str,
) -> DeleteQuizResponse:
    try:
        result = await quizzes_collection.delete_one({"_id": ObjectId(quiz_id)})
        if result.deleted_count:
            try:
                await dual_write_service.canonical_service.soft_delete_quiz_v2_by_legacy_mapping(
                    "quizzes",
                    quiz_id,
                )
            except Exception as exc:
                logger.exception(
                    "Manual quiz V2 soft delete failed after legacy delete for quiz_id=%s: %s",
                    quiz_id,
                    exc,
                )
            return DeleteQuizResponse(
                message=f"Quiz with ID {quiz_id} deleted successfully",
                delete_count=result.deleted_count,
            )
        return DeleteQuizResponse(
            message=f"No quiz found with ID {quiz_id}",
            delete_count=0,
        )
    except InvalidId as exc:
        logger.error("Invalid quiz ID: %s", exc)
    except PyMongoError as exc:
        logger.error("Error deleting quiz: %s", exc)
    return DeleteQuizResponse(
        message="An error occurred while deleting the quiz",
        delete_count=0,
    )


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
                canonical_quiz_id=quiz.get("canonical_quiz_id"),
                created_at=quiz["created_at"],
                updated_at=quiz["updated_at"],
                questions=quiz["questions"],
            )
            for quiz in quizzes
        ]
    except PyMongoError as exc:
        logger.error("Database error while listing quizzes: %s", exc)
    return []
