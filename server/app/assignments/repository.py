from bson import ObjectId
from fastapi import HTTPException

from server.app.assignments.statistics import recipient_statistics
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository


def page_query(query, cursor):
    if cursor is not None:
        if not ObjectId.is_valid(cursor):
            raise HTTPException(status_code=400, detail="Invalid pagination cursor")
        query = {**query, "_id": {"$lt": ObjectId(cursor)}}
    return query


async def page(collection, query, *, cursor=None, limit=25, projection=None):
    limit = max(1, min(limit, 100))
    rows = await collection.find(page_query(query, cursor), projection).sort("_id", -1).limit(limit + 1).to_list(length=limit + 1)
    return rows[:limit], str(rows[limit - 1]["_id"]) if len(rows) > limit else None


class AssignmentRepository:
    def __init__(self, training_repository, users, memberships, revisions):
        self.training = training_repository
        self.users = users
        self.memberships = memberships
        self.revisions = revisions

    async def active_recipients(self, organization_id, user_ids):
        ids = sorted(set(user_ids))
        if not ids or len(ids) > 1000 or any(not ObjectId.is_valid(value) for value in ids):
            raise HTTPException(status_code=400, detail="Assignments require between 1 and 1000 active organization recipients")
        members = await self.memberships.find({
            "organization_id": organization_id, "user_id": {"$in": ids}, "status": "active",
        }, {"user_id": 1}).to_list(length=len(ids) + 1)
        if {row["user_id"] for row in members} != set(ids):
            raise HTTPException(status_code=400, detail="All recipients must be active organization members")
        users = await self.users.find({
            "_id": {"$in": [ObjectId(value) for value in ids]}, "status": {"$ne": "deleted"},
        }, {"email": 1, "email_normalized": 1, "full_name": 1, "username": 1}).to_list(length=len(ids))
        if len(users) != len(ids) or any(not (row.get("email_normalized") or row.get("email")) for row in users):
            raise HTTPException(status_code=400, detail="One or more recipients are unavailable")
        return [{
            "user_id": str(row["_id"]),
            "email": str(row.get("email_normalized") or row["email"]).strip().lower(),
            "name": row.get("full_name") or row.get("username") or "Member",
        } for row in users]

    async def platform_library(self):
        return await self.training.quizzes_collection.database["organizations"].find_one({
            "system_key": "platform_library", "status": "active",
        }, {"_id": 1})

    async def library_quiz(self, quiz_id):
        library = await self.platform_library()
        if not library:
            return None
        quiz = await QuizV2Repository(self.training.quizzes_collection).find_public_shareable_by_id(quiz_id)
        if quiz is None:
            return None
        quiz = quiz.model_dump(by_alias=True)
        if (str(quiz.get("organization_id")) != str(library["_id"])
                or quiz.get("source") != "seed" or quiz.get("visibility") != "public"):
            return None
        return quiz

    async def run(self, organization_id, run_id):
        if not ObjectId.is_valid(run_id):
            return None
        return await self.training.runs_collection.find_one({
            "_id": ObjectId(run_id), "organization_id": organization_id,
            "delivery_kind": "quiz", "status": {"$in": ["open", "closed"]},
        })

    async def recipient(self, organization_id, run_id, user_id):
        return await self.training.assignments_collection.find_one({
            "organization_id": organization_id, "training_run_id": run_id, "recipient_user_id": user_id,
        })

    async def recipient_page(self, organization_id, run_id, *, cursor=None, limit=25):
        return await page(self.training.assignments_collection, {
            "organization_id": organization_id, "training_run_id": run_id,
        }, cursor=cursor, limit=limit)

    async def attempts(self, organization_id, run_id, recipient_id, user_id, *, cursor=None, limit=25):
        return await page(self.training.sessions_collection, {
            "organization_id": organization_id, "training_run_id": run_id, "user_id": user_id,
            "training_assignment_id": recipient_id,
        }, cursor=cursor, limit=limit, projection={
            "status": 1, "started_at": 1, "submitted_at": 1, "score": 1,
            "percentage": 1, "quiz_revision_id": 1, "expires_at": 1,
        })

    async def attempt(self, organization_id, run_id, recipient_id, user_id, session_id):
        if not ObjectId.is_valid(session_id):
            return None
        return await self.training.sessions_collection.find_one({
            "_id": ObjectId(session_id), "organization_id": organization_id,
            "training_run_id": run_id, "training_assignment_id": recipient_id, "user_id": user_id,
        })

    async def summaries(self, organization_id, runs):
        """One live aggregation plus a bounded frozen-summary projection per page."""
        open_ids = [str(run["_id"]) for run in runs if run["status"] == "open"]
        closed_ids = [str(run["_id"]) for run in runs if run["status"] == "closed"]
        result = {}
        if open_ids:
            completed = {"$or": [{"$eq": ["$status", "completed"]}, {"$ne": [{"$ifNull": ["$completed_at", None]}, None]}]}
            rows = await self.training.assignments_collection.aggregate([
                {"$match": {"organization_id": organization_id, "training_run_id": {"$in": open_ids}}},
                {"$group": {
                    "_id": "$training_run_id", "participant_count": {"$sum": 1},
                    "completed_count": {"$sum": {"$cond": [completed, 1, 0]}},
                    "average_percentage": {"$avg": {"$cond": [{"$and": [
                        completed, {"$isNumber": "$latest_percentage"},
                        {"$gte": ["$latest_percentage", 0]}, {"$lte": ["$latest_percentage", 100]},
                    ]}, "$latest_percentage", None]}},
                }},
            ]).to_list(length=len(open_ids))
            for row in rows:
                total, completed = row["participant_count"], row["completed_count"]
                result[row["_id"]] = {
                    "participant_count": total, "completed_count": completed,
                    "outstanding_count": total - completed,
                    "completion_percentage": round(completed * 100 / total, 2) if total else 0,
                    "average_percentage": round(row["average_percentage"], 2) if row["average_percentage"] is not None else None,
                }
            for run_id in open_ids:
                result.setdefault(run_id, recipient_statistics([]))
        if closed_ids:
            audits = await self.training.audit_events_collection.find({
                "organization_id": organization_id, "training_run_id": {"$in": closed_ids}, "event_type": "run_closed",
            }, {"training_run_id": 1, "payload.assignment_summary": 1}).to_list(length=len(closed_ids))
            for audit in audits:
                result[audit["training_run_id"]] = audit.get("payload", {}).get("assignment_summary")
        return result

    async def frozen_recipients(self, organization_id, run_id, *, cursor=None, limit=25):
        if cursor is not None and not ObjectId.is_valid(cursor):
            raise HTTPException(status_code=400, detail="Invalid pagination cursor")
        cursor = str(ObjectId(cursor)) if cursor is not None else None
        # Preserve a malformed/missing register as unavailable, never as an
        # empty successful report or an aggregation type error.
        valid_register = {"$isArray": "$payload.completion_register"}
        records = {"$cond": [valid_register, "$payload.completion_register", []]}
        if cursor:
            records = {"$filter": {"input": records, "as": "record", "cond": {"$lt": ["$$record.assignment_id", cursor]}}}
        rows = await self.training.audit_events_collection.aggregate([
            {"$match": {"organization_id": organization_id, "training_run_id": run_id, "event_type": "run_closed"}},
            {"$project": {"valid_register": valid_register, "records": {"$slice": [records, limit + 1]}}},
        ]).to_list(length=1)
        if not rows or not rows[0].get("valid_register") or not isinstance(rows[0].get("records"), list):
            raise HTTPException(status_code=503, detail="Final completion record is unavailable")
        records = rows[0]["records"]
        return records[:limit], records[limit - 1]["assignment_id"] if len(records) > limit else None

    async def frozen_user_rows(self, organization_id, run_ids, user_id):
        if not run_ids:
            return {}
        rows = await self.training.audit_events_collection.aggregate([
            {"$match": {"organization_id": organization_id, "training_run_id": {"$in": run_ids}, "event_type": "run_closed"}},
            {"$project": {"training_run_id": 1, "recipient": {"$arrayElemAt": [
                {"$filter": {"input": {"$cond": [
                    {"$isArray": "$payload.completion_register"}, "$payload.completion_register", [],
                ]}, "as": "record", "cond": {"$eq": ["$$record.recipient_user_id", user_id]}}}, 0,
            ]}}},
        ]).to_list(length=len(run_ids))
        return {row["training_run_id"]: row["recipient"] for row in rows if isinstance(row.get("recipient"), dict)}
