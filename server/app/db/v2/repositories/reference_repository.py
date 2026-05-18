from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from ..models.reference_models import (
    FolderDocumentV2,
    FolderItemDocumentV2,
    QuizHistoryDocumentV2,
    SavedQuizDocumentV2,
)


class ReferenceV2Repository:
    def __init__(
        self,
        folders_collection: AsyncIOMotorCollection,
        folder_items_collection: AsyncIOMotorCollection,
        saved_quizzes_collection: AsyncIOMotorCollection,
        quiz_history_collection: AsyncIOMotorCollection,
    ):
        self.folders_collection = folders_collection
        self.folder_items_collection = folder_items_collection
        self.saved_quizzes_collection = saved_quizzes_collection
        self.quiz_history_collection = quiz_history_collection

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @staticmethod
    def _merge_position(*values: Optional[int]) -> Optional[int]:
        valid_values = [value for value in values if value is not None]
        if not valid_values:
            return None
        return min(valid_values)

    @staticmethod
    def _active_query() -> dict:
        return {"$or": [{"deleted_at": {"$exists": False}}, {"deleted_at": None}]}

    async def insert_folder(self, folder: FolderDocumentV2) -> FolderDocumentV2:
        payload = folder.model_dump(by_alias=True)
        payload.pop("_id", None)
        created_at = payload.pop("created_at")
        updated_at = payload.pop("updated_at")
        existing = await self.folders_collection.find_one({"user_id": folder.user_id, "name": folder.name})
        if existing and existing.get("deleted_at") is not None:
            updates = {
                **payload,
                "created_at": existing.get("created_at", created_at),
                "updated_at": updated_at,
            }
            updates["deleted_at"] = None
            updated = await self.folders_collection.find_one_and_update(
                {"_id": existing["_id"]},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
            return FolderDocumentV2(**updated)
        result = await self.folders_collection.insert_one(
            {
                **payload,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        payload["_id"] = result.inserted_id
        payload["created_at"] = created_at
        payload["updated_at"] = updated_at
        return FolderDocumentV2(**payload)

    async def insert_folder_item(self, folder_item: FolderItemDocumentV2) -> FolderItemDocumentV2:
        payload = folder_item.model_dump(by_alias=True)
        result = await self.folder_items_collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return FolderItemDocumentV2(**payload)

    async def insert_saved_quiz(self, saved_quiz: SavedQuizDocumentV2) -> SavedQuizDocumentV2:
        payload = saved_quiz.model_dump(by_alias=True)
        result = await self.saved_quizzes_collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return SavedQuizDocumentV2(**payload)

    async def insert_quiz_history(self, quiz_history: QuizHistoryDocumentV2) -> QuizHistoryDocumentV2:
        payload = quiz_history.model_dump(by_alias=True)
        result = await self.quiz_history_collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return QuizHistoryDocumentV2(**payload)

    async def upsert_folder_by_legacy_id(self, folder: FolderDocumentV2) -> FolderDocumentV2:
        payload = folder.model_dump(by_alias=True)
        payload.pop("_id", None)
        existing = await self.folders_collection.find_one({"legacy_folder_id": folder.legacy_folder_id})
        if existing is not None and existing.get("deleted_at") is not None:
            payload["deleted_at"] = existing["deleted_at"]
        updated = await self.folders_collection.find_one_and_update(
            {"legacy_folder_id": folder.legacy_folder_id},
            {"$set": payload},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return FolderDocumentV2(**updated)

    async def get_folder_by_legacy_id(self, legacy_folder_id: str) -> FolderDocumentV2 | None:
        document = await self.folders_collection.find_one(
            {"$and": [{"legacy_folder_id": legacy_folder_id}, self._active_query()]}
        )
        return FolderDocumentV2(**document) if document else None

    async def get_folder_by_id(self, folder_id: str) -> FolderDocumentV2 | None:
        try:
            document = await self.folders_collection.find_one(
                {"$and": [{"_id": ObjectId(folder_id)}, self._active_query()]}
            )
        except InvalidId:
            return None
        return FolderDocumentV2(**document) if document else None

    async def get_folder_by_public_id(self, folder_id: str) -> FolderDocumentV2 | None:
        return await self.get_folder_by_legacy_id(folder_id) or await self.get_folder_by_id(folder_id)

    async def list_folders_for_user(self, user_id: str) -> list[FolderDocumentV2]:
        documents = await self.folders_collection.find(
            {"$and": [{"user_id": user_id}, self._active_query()]}
        ).to_list(length=500)
        return [FolderDocumentV2(**document) for document in documents]

    async def update_folder(
        self,
        folder_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        updated_at: Optional[datetime] = None,
    ) -> FolderDocumentV2 | None:
        updates = {
            key: value
            for key, value in {
                "name": name,
                "description": description,
                "updated_at": updated_at or datetime.utcnow(),
            }.items()
            if value is not None
        }
        try:
            updated = await self.folders_collection.find_one_and_update(
                {"_id": ObjectId(folder_id)},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            return None
        return FolderDocumentV2(**updated) if updated else None

    async def delete_folder_by_legacy_id(self, legacy_folder_id: str):
        folder = await self.folders_collection.find_one({"legacy_folder_id": legacy_folder_id})
        if folder:
            deleted_at = datetime.utcnow()
            await self.folder_items_collection.update_many(
                {"folder_id": str(folder["_id"]), **self._active_query()},
                {"$set": {"deleted_at": deleted_at}},
            )
            await self.folders_collection.update_one(
                {"_id": folder["_id"]},
                {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}},
            )

    async def delete_folder_by_id(self, folder_id: str):
        try:
            object_id = ObjectId(folder_id)
        except InvalidId:
            return
        deleted_at = datetime.utcnow()
        await self.folder_items_collection.update_many(
            {"folder_id": folder_id, **self._active_query()},
            {"$set": {"deleted_at": deleted_at}},
        )
        await self.folders_collection.update_one(
            {"_id": object_id, **self._active_query()},
            {"$set": {"deleted_at": deleted_at, "updated_at": deleted_at}},
        )

    async def delete_folder_by_public_id(self, folder_id: str):
        folder = await self.get_folder_by_public_id(folder_id)
        if folder:
            await self.delete_folder_by_id(str(folder.id))

    async def upsert_folder_item_by_legacy_id(
        self,
        folder_item: FolderItemDocumentV2,
        *,
        revive_deleted: bool = False,
    ) -> FolderItemDocumentV2:
        payload = folder_item.model_dump(by_alias=True)
        payload.pop("_id", None)
        created_at = payload.pop("created_at")
        deleted_at = payload.pop("deleted_at", None)
        legacy_match = None
        if folder_item.legacy_folder_item_id:
            legacy_match = await self.folder_items_collection.find_one(
                {"legacy_folder_item_id": folder_item.legacy_folder_item_id}
            )
        target_match = await self.folder_items_collection.find_one(
            {"folder_id": folder_item.folder_id, "quiz_id": folder_item.quiz_id}
        )

        if legacy_match and target_match and legacy_match["_id"] != target_match["_id"]:
            merged_created_at = min(
                self._normalize_datetime(created_at),
                self._normalize_datetime(legacy_match.get("created_at", created_at)),
                self._normalize_datetime(target_match.get("created_at", created_at)),
            )
            merged_position = self._merge_position(
                payload.get("position"),
                legacy_match.get("position"),
                target_match.get("position"),
            )
            target_legacy_item_id = target_match.get("legacy_folder_item_id")
            merged_display_title = (
                payload.get("display_title")
                or target_match.get("display_title")
                or legacy_match.get("display_title")
            )
            merged_deleted_at = target_match.get("deleted_at")
            if revive_deleted:
                merged_deleted_at = None
            updated = await self.folder_items_collection.find_one_and_update(
                {"_id": target_match["_id"]},
                {
                    "$set": {
                        **payload,
                        "created_at": merged_created_at,
                        "position": merged_position,
                        "display_title": merged_display_title,
                        "legacy_folder_item_id": target_legacy_item_id or folder_item.legacy_folder_item_id,
                        "deleted_at": merged_deleted_at,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            await self.folder_items_collection.delete_one({"_id": legacy_match["_id"]})
            return FolderItemDocumentV2(**updated)

        if legacy_match is not None:
            filter_query = {"_id": legacy_match["_id"]}
        elif target_match is not None:
            filter_query = {"_id": target_match["_id"]}
            if target_match.get("legacy_folder_item_id"):
                payload["legacy_folder_item_id"] = target_match["legacy_folder_item_id"]
            payload["position"] = self._merge_position(payload.get("position"), target_match.get("position"))
            payload["display_title"] = payload.get("display_title") or target_match.get("display_title")
        else:
            filter_query = (
                {"legacy_folder_item_id": folder_item.legacy_folder_item_id}
                if folder_item.legacy_folder_item_id
                else {"folder_id": folder_item.folder_id, "quiz_id": folder_item.quiz_id}
            )
        if revive_deleted:
            payload["deleted_at"] = None
        elif legacy_match is not None and legacy_match.get("deleted_at") is not None:
            payload["deleted_at"] = legacy_match.get("deleted_at")
        elif target_match is not None and target_match.get("deleted_at") is not None:
            payload["deleted_at"] = target_match.get("deleted_at")
        elif deleted_at is not None:
            payload["deleted_at"] = deleted_at
        updated = await self.folder_items_collection.find_one_and_update(
            filter_query,
            {"$set": payload, "$setOnInsert": {"created_at": created_at}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return FolderItemDocumentV2(**updated)

    async def get_folder_item_by_legacy_id(self, legacy_folder_item_id: str) -> FolderItemDocumentV2 | None:
        document = await self.folder_items_collection.find_one(
            {"$and": [{"legacy_folder_item_id": legacy_folder_item_id}, self._active_query()]}
        )
        return FolderItemDocumentV2(**document) if document else None

    async def get_folder_item_by_id(self, folder_item_id: str) -> FolderItemDocumentV2 | None:
        try:
            document = await self.folder_items_collection.find_one(
                {"$and": [{"_id": ObjectId(folder_item_id)}, self._active_query()]}
            )
        except InvalidId:
            return None
        return FolderItemDocumentV2(**document) if document else None

    async def get_folder_item_by_public_id(self, folder_item_id: str) -> FolderItemDocumentV2 | None:
        return await self.get_folder_item_by_legacy_id(folder_item_id) or await self.get_folder_item_by_id(
            folder_item_id
        )

    async def list_folder_items_for_folder(self, folder_id: str) -> list[FolderItemDocumentV2]:
        documents = await self.folder_items_collection.find(
            {"$and": [{"folder_id": folder_id}, self._active_query()]}
        ).to_list(length=1000)
        return [FolderItemDocumentV2(**document) for document in documents]

    async def delete_folder_item_by_legacy_id(self, legacy_folder_item_id: str):
        await self.folder_items_collection.update_one(
            {"legacy_folder_item_id": legacy_folder_item_id, **self._active_query()},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )

    async def update_folder_item(
        self,
        folder_item_id: str,
        *,
        folder_id: Optional[str] = None,
        quiz_id: Optional[str] = None,
        added_by: Optional[str] = None,
        position: Optional[int] = None,
        display_title: Optional[str] = None,
    ) -> FolderItemDocumentV2 | None:
        updates = {
            key: value
            for key, value in {
                "folder_id": folder_id,
                "quiz_id": quiz_id,
                "added_by": added_by,
                "position": position,
                "display_title": display_title,
            }.items()
            if value is not None
        }
        try:
            updated = await self.folder_items_collection.find_one_and_update(
                {"_id": ObjectId(folder_item_id)},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            return None
        return FolderItemDocumentV2(**updated) if updated else None

    async def delete_folder_item_by_id(self, folder_item_id: str):
        try:
            object_id = ObjectId(folder_item_id)
        except InvalidId:
            return
        await self.folder_items_collection.update_one(
            {"_id": object_id, **self._active_query()},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )

    async def delete_folder_item_by_public_id(self, folder_item_id: str):
        item = await self.get_folder_item_by_public_id(folder_item_id)
        if item:
            await self.delete_folder_item_by_id(str(item.id))

    async def upsert_saved_quiz(
        self,
        saved_quiz: SavedQuizDocumentV2,
        *,
        revive_deleted: bool = False,
    ) -> SavedQuizDocumentV2:
        payload = saved_quiz.model_dump(by_alias=True)
        payload.pop("_id", None)
        saved_at = payload.pop("saved_at")
        deleted_at = payload.pop("deleted_at", None)
        legacy_match = None
        if saved_quiz.legacy_saved_quiz_id:
            legacy_match = await self.saved_quizzes_collection.find_one(
                {"legacy_saved_quiz_id": saved_quiz.legacy_saved_quiz_id}
            )
        target_match = await self.saved_quizzes_collection.find_one(
            {"user_id": saved_quiz.user_id, "quiz_id": saved_quiz.quiz_id}
        )

        if legacy_match and target_match and legacy_match["_id"] != target_match["_id"]:
            merged_saved_at = min(
                self._normalize_datetime(saved_at),
                self._normalize_datetime(legacy_match.get("saved_at", saved_at)),
                self._normalize_datetime(target_match.get("saved_at", saved_at)),
            )
            merged_display_title = (
                payload.get("display_title")
                or target_match.get("display_title")
                or legacy_match.get("display_title")
            )
            merged_deleted_at = target_match.get("deleted_at")
            if revive_deleted:
                merged_deleted_at = None
            updated = await self.saved_quizzes_collection.find_one_and_update(
                {"_id": target_match["_id"]},
                {
                    "$set": {
                        **payload,
                        "display_title": merged_display_title,
                        "saved_at": merged_saved_at,
                        "deleted_at": merged_deleted_at,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            await self.saved_quizzes_collection.delete_one({"_id": legacy_match["_id"]})
            return SavedQuizDocumentV2(**updated)

        if legacy_match is not None:
            filter_query = {"_id": legacy_match["_id"]}
        elif target_match is not None:
            filter_query = {"_id": target_match["_id"]}
            payload["display_title"] = payload.get("display_title") or target_match.get("display_title")
        else:
            filter_query = (
                {"legacy_saved_quiz_id": saved_quiz.legacy_saved_quiz_id}
                if saved_quiz.legacy_saved_quiz_id
                else {"user_id": saved_quiz.user_id, "quiz_id": saved_quiz.quiz_id}
            )
        if revive_deleted:
            payload["deleted_at"] = None
        elif legacy_match is not None and legacy_match.get("deleted_at") is not None:
            payload["deleted_at"] = legacy_match.get("deleted_at")
        elif target_match is not None and target_match.get("deleted_at") is not None:
            payload["deleted_at"] = target_match.get("deleted_at")
        elif deleted_at is not None:
            payload["deleted_at"] = deleted_at
        updated = await self.saved_quizzes_collection.find_one_and_update(
            filter_query,
            {"$set": payload, "$setOnInsert": {"saved_at": saved_at}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return SavedQuizDocumentV2(**updated)

    async def list_saved_quizzes_for_user(self, user_id: str) -> list[SavedQuizDocumentV2]:
        documents = await self.saved_quizzes_collection.find(
            {"$and": [{"user_id": user_id}, self._active_query()]}
        ).to_list(length=500)
        return [SavedQuizDocumentV2(**document) for document in documents]

    async def get_saved_quiz_by_legacy_id(
        self,
        legacy_saved_quiz_id: str,
        user_id: Optional[str] = None,
    ) -> SavedQuizDocumentV2 | None:
        query: dict[str, str] = {"legacy_saved_quiz_id": legacy_saved_quiz_id}
        if user_id is not None:
            query["user_id"] = user_id
        document = await self.saved_quizzes_collection.find_one({"$and": [query, self._active_query()]})
        return SavedQuizDocumentV2(**document) if document else None

    async def get_saved_quiz_by_id(
        self,
        saved_quiz_id: str,
        user_id: Optional[str] = None,
    ) -> SavedQuizDocumentV2 | None:
        query: dict[str, object] = {}
        try:
            query["_id"] = ObjectId(saved_quiz_id)
        except InvalidId:
            return None
        if user_id is not None:
            query["user_id"] = user_id
        document = await self.saved_quizzes_collection.find_one({"$and": [query, self._active_query()]})
        return SavedQuizDocumentV2(**document) if document else None

    async def get_saved_quiz_by_public_id(
        self,
        saved_quiz_id: str,
        user_id: Optional[str] = None,
    ) -> SavedQuizDocumentV2 | None:
        return await self.get_saved_quiz_by_legacy_id(saved_quiz_id, user_id=user_id) or await self.get_saved_quiz_by_id(
            saved_quiz_id,
            user_id=user_id,
        )

    async def delete_saved_quiz(self, user_id: str, quiz_id: str):
        await self.saved_quizzes_collection.update_one(
            {"user_id": user_id, "quiz_id": quiz_id, **self._active_query()},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )

    async def delete_saved_quiz_by_id(
        self,
        saved_quiz_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> int:
        query: dict[str, object] = {}
        try:
            query["_id"] = ObjectId(saved_quiz_id)
        except InvalidId:
            return 0
        if user_id is not None:
            query["user_id"] = user_id
        result = await self.saved_quizzes_collection.update_one(
            {"$and": [query, self._active_query()]},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )
        return result.modified_count

    async def upsert_quiz_history(self, quiz_history: QuizHistoryDocumentV2) -> QuizHistoryDocumentV2:
        payload = quiz_history.model_dump(by_alias=True)
        payload.pop("_id", None)
        created_at = payload.pop("created_at")
        existing = await self.quiz_history_collection.find_one({"legacy_history_id": quiz_history.legacy_history_id})
        if existing is not None and existing.get("deleted_at") is not None:
            payload["deleted_at"] = existing["deleted_at"]
        updated = await self.quiz_history_collection.find_one_and_update(
            {"legacy_history_id": quiz_history.legacy_history_id},
            {"$set": payload, "$setOnInsert": {"created_at": created_at}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return QuizHistoryDocumentV2(**updated)

    async def list_quiz_history_for_user(self, user_id: str) -> list[QuizHistoryDocumentV2]:
        documents = await self.quiz_history_collection.find(
            {"$and": [{"user_id": user_id}, self._active_query()]}
        ).to_list(length=500)
        return [QuizHistoryDocumentV2(**document) for document in documents]

    async def soft_delete_quiz_history_by_id(
        self,
        history_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> int:
        query: dict[str, object] = {}
        try:
            query["_id"] = ObjectId(history_id)
        except InvalidId:
            return 0
        if user_id is not None:
            query["user_id"] = user_id
        result = await self.quiz_history_collection.update_one(
            {"$and": [query, self._active_query()]},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )
        return result.modified_count
