from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from server.app.assignments.models import QuizRevisionDocument


class QuizRevisionRepository:
    """Append-only, tenant-local content-addressed delivery revisions."""

    def __init__(self, collection):
        self.collection = collection

    async def snapshot(self, organization_id, quiz, created_by_user_id):
        snapshot = {
            "title": quiz.get("title", "Quiz"),
            "quiz_type": getattr(quiz.get("quiz_type"), "value", quiz.get("quiz_type")),
            "questions": deepcopy(quiz.get("questions") or []),
        }
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
        content_hash = hashlib.sha256(encoded.encode()).hexdigest()
        query = {"organization_id": organization_id, "quiz_id": str(quiz["_id"]), "content_hash": content_hash}
        document = QuizRevisionDocument(
            **query, snapshot=snapshot, created_by_user_id=created_by_user_id,
            created_at=datetime.now(timezone.utc),
        ).model_dump(by_alias=True)
        try:
            return await self.collection.find_one_and_update(
                query,
                {"$setOnInsert": document},
                upsert=True, return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            existing = await self.collection.find_one(query)
            if existing is None:
                raise
            return existing
