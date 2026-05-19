from __future__ import annotations

from datetime import timedelta

from pymongo.errors import DuplicateKeyError

from .types import utcnow


class MigrationLockError(RuntimeError):
    pass


class MigrationLockService:
    def __init__(self, database):
        self.database = database
        self.locks = database["migration_locks"]
        self.runs = database["migration_runs"]

    async def ensure_indexes(self):
        await self.locks.create_index("expires_at", expireAfterSeconds=0, name="expires_at_ttl")
        await self.runs.create_index(
            [("migration_name", 1), ("started_at", -1)],
            name="migration_name_started_at_idx",
        )

    async def acquire_lock(
        self,
        *,
        migration_name: str,
        run_id: str,
        dry_run: bool,
        triggered_by: str,
        lease_seconds: int,
    ):
        await self.ensure_indexes()
        now = utcnow()
        expires_at = now + timedelta(seconds=lease_seconds)
        lock_doc = {
            "_id": migration_name,
            "run_id": run_id,
            "dry_run": dry_run,
            "triggered_by": triggered_by,
            "started_at": now,
            "expires_at": expires_at,
        }
        try:
            await self.locks.insert_one(lock_doc)
        except DuplicateKeyError as exc:
            active = await self.locks.find_one({"_id": migration_name})
            raise MigrationLockError(
                f"Migration '{migration_name}' is already running with run_id={active.get('run_id')}"
            ) from exc

        await self.runs.insert_one(
            {
                "_id": run_id,
                "migration_name": migration_name,
                "status": "running",
                "dry_run": dry_run,
                "triggered_by": triggered_by,
                "started_at": now,
            }
        )

    async def renew_lock(self, *, migration_name: str, run_id: str, lease_seconds: int):
        expires_at = utcnow() + timedelta(seconds=lease_seconds)
        await self.locks.update_one(
            {"_id": migration_name, "run_id": run_id},
            {"$set": {"expires_at": expires_at}},
        )

    async def release_lock(
        self,
        *,
        migration_name: str,
        run_id: str,
        status: str,
        summary: dict | None = None,
        error: str | None = None,
    ):
        now = utcnow()
        await self.runs.update_one(
            {"_id": run_id},
            {
                "$set": {
                    "status": status,
                    "completed_at": now,
                    "summary": summary,
                    "error": error,
                }
            },
        )
        await self.locks.delete_one({"_id": migration_name, "run_id": run_id})

    async def get_last_run(self, migration_name: str):
        return await self.runs.find_one(
            {"migration_name": migration_name},
            sort=[("started_at", -1)],
        )
