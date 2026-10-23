from __future__ import annotations

from datetime import timedelta

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .types import utcnow


class MigrationLockError(RuntimeError):
    pass


class MigrationLockLostError(MigrationLockError):
    """Raised when a worker can no longer prove ownership of its lease."""

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
        run_document = {
            "_id": run_id,
            "migration_name": migration_name,
            "status": "acquiring",
            "dry_run": dry_run,
            "triggered_by": triggered_by,
            "started_at": now,
        }
        try:
            await self.runs.insert_one(run_document)
        except DuplicateKeyError:
            # Lock-acquisition backoff reuses the external run id so the
            # deployment has one auditable migration attempt. A crashed
            # process can also leave a pre-lock ``acquiring`` row behind;
            # reclaim it only after the original lease window has elapsed.
            stale_acquiring_before = now - timedelta(seconds=lease_seconds)
            retry = await self.runs.update_one(
                {
                    "_id": run_id,
                    "migration_name": migration_name,
                    "lock_acquired_at": {"$exists": False},
                    "$or": [
                        {"status": "failed"},
                        {
                            "status": "acquiring",
                            "started_at": {"$lte": stale_acquiring_before},
                        },
                    ],
                },
                {
                    "$set": {
                        "status": "acquiring",
                        "started_at": now,
                    },
                    "$unset": {"completed_at": "", "error": ""},
                },
            )
            if retry.matched_count != 1:
                raise MigrationLockError(
                    f"Migration run_id={run_id} cannot be retried"
                )
        try:
            await self.locks.insert_one(lock_doc)
        except DuplicateKeyError as exc:
            # Mongo's TTL monitor is eventually consistent. Explicitly reclaim
            # only an expired lease so a crashed process cannot block a later
            # deployment until the monitor happens to remove its lock row.
            replaced = await self.locks.find_one_and_replace(
                {"_id": migration_name, "expires_at": {"$lte": now}},
                lock_doc,
                return_document=ReturnDocument.BEFORE,
            )
            if replaced is None:
                # TTL cleanup may remove an expired document between the
                # duplicate insert and reclaim attempt. Retry acquisition once
                # before reporting an active migration.
                try:
                    await self.locks.insert_one(lock_doc)
                except DuplicateKeyError:
                    active = await self.locks.find_one({"_id": migration_name})
                    await self._mark_acquire_failed(run_id, now, "Migration lock is already held")
                    active_run_id = active.get("run_id") if active else "unknown"
                    raise MigrationLockError(
                        f"Migration '{migration_name}' is already running with run_id={active_run_id}"
                    ) from exc
            else:
                await self.runs.update_one(
                    {"_id": replaced["run_id"], "status": {"$in": ["acquiring", "running"]}},
                    {
                        "$set": {
                            "status": "abandoned",
                            "completed_at": now,
                            "error": "Migration lease expired before completion",
                        }
                    },
                )
        except Exception:
            await self._mark_acquire_failed(run_id, now, "Could not acquire migration lock")
            raise

        run_started = await self.runs.update_one(
            {"_id": run_id, "status": "acquiring"},
            {"$set": {"status": "running", "lock_acquired_at": now}},
        )
        if run_started.matched_count != 1:
            await self.locks.delete_one({"_id": migration_name, "run_id": run_id})
            await self._mark_acquire_failed(
                run_id,
                utcnow(),
                "Could not record migration lock ownership",
            )
            raise MigrationLockError(
                f"Migration '{migration_name}' could not record lock ownership"
            )

    async def _mark_acquire_failed(self, run_id: str, now, error: str) -> None:
        await self.runs.update_one(
            {"_id": run_id, "status": "acquiring"},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": now,
                    "error": error,
                }
            },
        )

    async def renew_lock(self, *, migration_name: str, run_id: str, lease_seconds: int):
        expires_at = utcnow() + timedelta(seconds=lease_seconds)
        result = await self.locks.update_one(
            {"_id": migration_name, "run_id": run_id},
            {"$set": {"expires_at": expires_at}},
        )
        if result.matched_count != 1:
            raise MigrationLockLostError(
                f"Migration '{migration_name}' no longer owns lease run_id={run_id}"
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
            {"_id": run_id, "status": {"$in": ["acquiring", "running"]}},
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

    async def get_latest_completed_run(self, migration_name: str):
        """Return the last successful non-dry-run execution for a migration."""
        return await self.runs.find_one(
            {
                "migration_name": migration_name,
                "status": "completed",
                "dry_run": False,
            },
            sort=[("completed_at", -1)],
        )

    async def get_latest_blocked_run(self, migration_name: str):
        """Return an unresolved legacy-data outcome awaiting deliberate repair."""
        return await self.runs.find_one(
            {
                "migration_name": migration_name,
                "status": "blocked",
                "dry_run": False,
            },
            sort=[("completed_at", -1)],
        )

    async def get_latest_terminal_run(self, migration_name: str):
        """Return the latest completed or blocked deployment outcome.

        Older blocked runs are historical once a later full reconciliation has
        completed. Callers that gate migrations must therefore inspect the
        most recent terminal outcome rather than querying each status
        independently.
        """
        return await self.runs.find_one(
            {
                "migration_name": migration_name,
                "status": {"$in": ["completed", "blocked"]},
                "dry_run": False,
            },
            sort=[("completed_at", -1)],
        )
