from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository


class LiveQuizSessionRepository:
    def __init__(
        self,
        quizzes_v2_collection: AsyncIOMotorCollection,
        sessions_collection: AsyncIOMotorCollection,
    ):
        self.quiz_repository = QuizV2Repository(quizzes_v2_collection)
        self.sessions_collection = sessions_collection

    async def get_quiz_by_id(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        quiz = await self.quiz_repository.find_by_id(quiz_id)
        return quiz.model_dump(by_alias=True) if quiz else None

    async def get_quiz_by_access_code(self, access_code: str) -> Optional[Dict[str, Any]]:
        quiz = await self.quiz_repository.find_by_access_code(access_code.strip().upper())
        return quiz.model_dump(by_alias=True) if quiz else None

    async def access_code_exists(self, access_code: str) -> bool:
        return await self.quiz_repository.access_code_exists(access_code)

    async def list_live_quizzes_by_creator(
        self,
        creator_user_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        cursor = self.quiz_repository.collection.find(
            {
                "live_quiz_enabled": True,
                "status": {"$ne": "deleted"},
                "$or": [
                    {"owner_user_id": creator_user_id},
                    {"created_by": creator_user_id},
                    {"owner_id": creator_user_id},
                ],
            }
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def enable_live_quiz(
        self,
        quiz_id: str,
        access_code: str,
        time_limit_minutes: int,
        access_code_expires_at: datetime,
        creator_id: str,
        participant_access_mode: str = "public",
        invited_participant_emails: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        updated = await self.quiz_repository.enable_live_quiz(
            quiz_id,
            access_code=access_code,
            time_limit_minutes=time_limit_minutes,
            access_code_expires_at=access_code_expires_at,
            participant_access_mode=participant_access_mode,
            invited_participant_emails=invited_participant_emails or [],
        )
        return updated.model_dump(by_alias=True) if updated else None

    async def create_session(self, session_data: Dict[str, Any]) -> str:
        result = await self.sessions_collection.insert_one(session_data)
        return str(result.inserted_id)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.sessions_collection.find_one({"_id": ObjectId(session_id)})
        except InvalidId:
            return None

    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        try:
            updates["updated_at"] = datetime.now(timezone.utc)
            return await self.sessions_collection.find_one_and_update(
                {"_id": ObjectId(session_id)},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            return None

    async def save_answer(
        self,
        session_id: str,
        question_index: int,
        selected_answer: str,
        next_question_index: int,
    ) -> Optional[Dict[str, Any]]:
        session = await self.get_session(session_id)
        if not session:
            return None

        now = datetime.now(timezone.utc)
        answers = [
            answer
            for answer in session.get("answers", [])
            if answer.get("question_index") != question_index
        ]
        answers.append(
            {
                "question_index": question_index,
                "selected_answer": selected_answer,
                "answered_at": now,
            }
        )
        answers.sort(key=lambda answer: answer["question_index"])
        return await self.update_session(
            session_id,
            {
                "answers": answers,
                "current_question_index": next_question_index,
                "status": "active",
            },
        )

    async def list_quiz_sessions(self, quiz_id: str) -> List[Dict[str, Any]]:
        cursor = self.sessions_collection.find({"quiz_id": quiz_id}).sort(
            "created_at", -1,
        )
        return await cursor.to_list(length=500)

    async def list_quiz_sessions_by_creator(self, quiz_id: str, creator_user_id: str) -> List[Dict[str, Any]]:
        """List sessions for a quiz, filtered by creator_user_id for security."""
        cursor = self.sessions_collection.find(
            {"quiz_id": quiz_id, "creator_user_id": creator_user_id}
        ).sort("created_at", -1)
        return await cursor.to_list(length=500)

    async def get_session_by_id_and_creator(self, session_id: str, creator_user_id: str) -> Optional[Dict[str, Any]]:
        """Get a session ensuring it belongs to the creator."""
        try:
            return await self.sessions_collection.find_one(
                {"_id": ObjectId(session_id), "creator_user_id": creator_user_id}
            )
        except InvalidId:
            return None

    async def find_live_quiz_sessions_for_user(
        self,
        user_email: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Find sessions where the participant email matches a user's email."""
        cursor = self.sessions_collection.find(
            {"participant_email": user_email.strip().lower()}
        ).sort("submitted_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
