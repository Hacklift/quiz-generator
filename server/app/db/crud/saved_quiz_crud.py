from bson import ObjectId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from ....app.db.core.connection import get_saved_quizzes_collection
from ....app.db.models.saved_quiz_model import SavedQuizModel, QuizQuestionModel
from pydantic import ValidationError

collection = get_saved_quizzes_collection()

def model_to_dict(model):
    dump_fn = getattr(model, "model_dump", None)
    if callable(dump_fn):
        return model.model_dump(by_alias=True, exclude_none=True)
    else:
        return model.dict(by_alias=True, exclude_none=True)

async def save_quiz(user_id: str, title: str, question_type: str, questions: list):
    try:
        parsed_questions = [QuizQuestionModel(**q) if isinstance(q, dict) else q for q in questions]
        quiz = SavedQuizModel(
            user_id=user_id,
            title=title,
            question_type=question_type,
            questions=parsed_questions,
            created_at=datetime.utcnow(),
        )
        doc = model_to_dict(quiz)
        if "_id" in doc and doc["_id"] is None:
            doc.pop("_id")
        result = await collection.insert_one(doc)
        return str(result.inserted_id)
    except ValidationError as ve:
        raise Exception(f"Validation error: {ve}")
    except Exception as e:
        raise

async def get_saved_quizzes(user_id: str):
    quizzes = await collection.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    for q in quizzes:
        q["_id"] = str(q["_id"])
    return quizzes

async def delete_saved_quiz(quiz_id: str, user_id: str):
    result = await collection.delete_one({"_id": ObjectId(quiz_id), "user_id": user_id})
    return result.deleted_count > 0

async def get_saved_quiz_by_id(quiz_id: str, user_id: str):
    quiz = await collection.find_one({"_id": ObjectId(quiz_id), "user_id": user_id})
    if quiz:
        quiz["_id"] = str(quiz["_id"])
    return quiz
