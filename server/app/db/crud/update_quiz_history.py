from typing import Dict, Any
from ....app.db.core.connection import quiz_history_collection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def update_quiz_history(quiz_data: Dict[str, Any]):
    quiz_data["created_at"] = datetime.utcnow()

    result = await quiz_history_collection.insert_one(quiz_data)
    logger.info("Quiz saved for user %s: %s", quiz_data.get("user_id"), str(result.inserted_id))
    
    return str(result.inserted_id)



async def get_quiz_history(user_id: str, limit: int = 100):
    cursor = (
    quiz_history_collection
        .find({"user_id": user_id})
        .sort("created_at", -1)
)

    quizzes = await cursor.to_list(length=limit)
    
    for q in quizzes:
        q["_id"] = str(q["_id"])
        if isinstance(q.get("created_at"), datetime):
            q["created_at"] = q["created_at"].isoformat()
    return quizzes
