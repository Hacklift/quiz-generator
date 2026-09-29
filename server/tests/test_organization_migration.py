from __future__ import annotations

import os
from datetime import timedelta
from types import SimpleNamespace

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EMAIL_SENDER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("EMAIL_HOST", "smtp.example.com")
os.environ.setdefault("EMAIL_PORT", "587")
os.environ.setdefault("SHARE_URL", "http://localhost:3000")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

import pytest
from bson import ObjectId

from server.scripts.migrations.organizations import backfill_organizations as migration_module
from server.scripts.migrations.organizations.backfill_organizations import (
    OrganizationBackfillBlockedError,
    _backfill_missing_session_organizations,
    _reconcile_users,
    backfill_organizations,
)
from server.scripts.migrations.v2.migration.lock import (
    MigrationLockError,
    MigrationLockLostError,
    MigrationLockService,
)
from server.scripts.migrations.v2.migration.types import utcnow


def _matches(document: dict, query: dict) -> bool:
    for key, expected in query.items():
        value = document.get(key)
        if isinstance(expected, dict):
            if "$gt" in expected and not value > expected["$gt"]:
                return False
            if "$lte" in expected and not value <= expected["$lte"]:
                return False
            if "$in" in expected and value not in expected["$in"]:
                return False
        elif value != expected:
            return False
    return True


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)
        self._limit = None

    def sort(self, key, direction):
        self.documents.sort(key=lambda document: document[key], reverse=direction < 0)
        return self

    def limit(self, value):
        self._limit = value
        return self

    async def to_list(self, length):
        limit = self._limit if self._limit is not None else length
        return self.documents[: min(length, limit)]


class FakeCollection:
    def __init__(self, documents=()):
        self.documents = list(documents)
        self.write_calls = 0

    def find(self, query):
        return FakeCursor(document for document in self.documents if _matches(document, query))

    async def find_one(self, query, **_kwargs):
        return next((document for document in self.documents if _matches(document, query)), None)


class FakeDatabase:
    def __init__(self, *, users, organizations=(), memberships=()):
        self.collections = {
            "users": FakeCollection(users),
            "organizations": FakeCollection(organizations),
            "organization_memberships": FakeCollection(memberships),
        }

    def __getitem__(self, name):
        return self.collections[name]


@pytest.mark.asyncio
async def test_organization_dry_run_is_read_only_and_batches_reconciliation():
    database = FakeDatabase(
        users=[
            {"_id": ObjectId(), "username": "ada"},
            {"_id": ObjectId(), "username": "lin"},
        ]
    )

    report = await backfill_organizations(
        dry_run=True,
        batch_size=1,
        database_instance=database,
    )

    assert report.scanned_users == 2
    assert report.provisioned_users == 2
    assert report.platform_library_created
    assert all(collection.write_calls == 0 for collection in database.collections.values())


@pytest.mark.asyncio
async def test_dry_run_rejects_a_conflicting_default_organization_without_writing():
    user_id = str(ObjectId())
    database = FakeDatabase(
        users=[{"_id": ObjectId(user_id), "username": "ada", "default_organization_id": "other"}],
    )

    report = await backfill_organizations(dry_run=True, database_instance=database)

    assert report.unresolved_count == 1
    assert all(collection.write_calls == 0 for collection in database.collections.values())


@pytest.mark.asyncio
async def test_session_backfill_only_populates_missing_active_organization_selector():
    class SessionsCollection:
        def __init__(self):
            self.query = None
            self.update = None

        async def update_many(self, query, update):
            self.query = query
            self.update = update
            return type("Result", (), {"modified_count": 2})()

    sessions = SessionsCollection()
    updated = await _backfill_missing_session_organizations(
        db={"user_sessions": sessions},
        user_id="user-1",
        organization_id="organization-1",
    )

    assert updated == 2
    assert sessions.query["user_id"] == "user-1"
    assert sessions.query["$or"] == [
        {"active_organization_id": {"$exists": False}},
        {"active_organization_id": None},
    ]
    assert sessions.update == {"$set": {"active_organization_id": "organization-1"}}


@pytest.mark.asyncio
async def test_dry_run_strictly_rejects_a_conflicting_default_organization_without_writing():
    user_id = str(ObjectId())
    database = FakeDatabase(
        users=[{"_id": ObjectId(user_id), "username": "ada", "default_organization_id": "other"}],
    )

    with pytest.raises(OrganizationBackfillBlockedError, match="default_organization_does_not_match"):
        await backfill_organizations(dry_run=True, strict=True, database_instance=database)

    assert all(collection.write_calls == 0 for collection in database.collections.values())


@pytest.mark.asyncio
async def test_write_mode_records_blocked_preflight_without_tenant_writes(monkeypatch):
    user_id = ObjectId()
    database = FakeDatabase(
        users=[{"_id": user_id, "username": "ada", "default_organization_id": "other"}],
    )

    class FakeMigrationLock:
        async def ensure_indexes(self):
            return None

        async def get_latest_completed_run(self, _migration_name):
            return None

        async def get_latest_blocked_run(self, _migration_name):
            return None

        async def acquire_lock(self, **_kwargs):
            return None

        async def renew_lock(self, **_kwargs):
            return None

        async def release_lock(self, **_kwargs):
            return None

    async def ensure_collections(*_args):
        return None

    monkeypatch.setattr(migration_module, "MigrationLockService", lambda _db: FakeMigrationLock())
    monkeypatch.setattr(migration_module, "ensure_organization_collections", ensure_collections)

    report = await backfill_organizations(dry_run=False, database_instance=database)

    assert all(collection.write_calls == 0 for collection in database.collections.values())
    assert report.blocked
    assert report.unresolved_count == 1


@pytest.mark.asyncio
async def test_strict_write_mode_rejects_blocked_preflight_without_tenant_writes(monkeypatch):
    user_id = ObjectId()
    database = FakeDatabase(
        users=[{"_id": user_id, "username": "ada", "default_organization_id": "other"}],
    )

    class FakeMigrationLock:
        async def ensure_indexes(self):
            return None

        async def get_latest_completed_run(self, _migration_name):
            return None

        async def get_latest_blocked_run(self, _migration_name):
            return None

        async def acquire_lock(self, **_kwargs):
            return None

        async def renew_lock(self, **_kwargs):
            return None

        async def release_lock(self, **_kwargs):
            return None

    async def ensure_collections(*_args):
        return None

    monkeypatch.setattr(migration_module, "MigrationLockService", lambda _db: FakeMigrationLock())
    monkeypatch.setattr(migration_module, "ensure_organization_collections", ensure_collections)

    with pytest.raises(OrganizationBackfillBlockedError, match="default_organization_does_not_match"):
        await backfill_organizations(dry_run=False, strict=True, database_instance=database)

    assert all(collection.write_calls == 0 for collection in database.collections.values())


@pytest.mark.asyncio
async def test_strict_mode_rejects_a_previously_recorded_blocked_run(monkeypatch):
    database = FakeDatabase(users=[])

    class FakeMigrationLock:
        async def ensure_indexes(self):
            return None

        async def get_latest_completed_run(self, _migration_name):
            return None

        async def get_latest_blocked_run(self, _migration_name):
            return {
                "summary": {
                    "unresolved_count": 1,
                    "unresolved_examples": [
                        {
                            "record_id": "user-1",
                            "reason": "default_organization_does_not_match_personal_organization",
                        }
                    ],
                }
            }

    async def ensure_collections(*_args):
        return None

    monkeypatch.setattr(migration_module, "MigrationLockService", lambda _db: FakeMigrationLock())
    monkeypatch.setattr(migration_module, "ensure_organization_collections", ensure_collections)

    with pytest.raises(OrganizationBackfillBlockedError, match="default_organization_does_not_match"):
        await backfill_organizations(dry_run=False, strict=True, database_instance=database)


@pytest.mark.asyncio
async def test_non_strict_mode_reuses_blocked_report_without_rescanning(monkeypatch):
    database = FakeDatabase(users=[{"_id": ObjectId(), "username": "should-not-be-scanned"}])

    class FakeMigrationLock:
        async def ensure_indexes(self):
            return None

        async def get_latest_completed_run(self, _migration_name):
            return None

        async def get_latest_blocked_run(self, _migration_name):
            return {
                "summary": {
                    "unresolved_count": 1,
                    "unresolved_examples": [
                        {
                            "record_id": "user-1",
                            "reason": "personal_organization_is_not_active",
                        }
                    ],
                }
            }

    async def ensure_collections(*_args):
        return None

    monkeypatch.setattr(migration_module, "MigrationLockService", lambda _db: FakeMigrationLock())
    monkeypatch.setattr(migration_module, "ensure_organization_collections", ensure_collections)

    report = await backfill_organizations(dry_run=False, database_instance=database)

    assert report.already_blocked
    assert report.blocked
    assert report.scanned_users == 0
    assert report.unresolved_count == 1
    assert all(collection.write_calls == 0 for collection in database.collections.values())


class FakeLockCollection:
    def __init__(self, document=None):
        self.document = document

    async def create_index(self, *_args, **_kwargs):
        return None

    async def insert_one(self, document):
        if self.document is not None:
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("duplicate")
        self.document = dict(document)

    async def find_one_and_replace(self, query, replacement, **_kwargs):
        if self.document is None or not _matches(self.document, query):
            return None
        previous = self.document
        self.document = dict(replacement)
        return previous

    async def find_one(self, query, **_kwargs):
        return self.document if self.document is not None and _matches(self.document, query) else None

    async def update_one(self, query, update):
        if self.document is None or not _matches(self.document, query):
            return SimpleNamespace(matched_count=0)
        self.document.update(update["$set"])
        return SimpleNamespace(matched_count=1)

    async def delete_one(self, query):
        if self.document is not None and _matches(self.document, query):
            self.document = None


class FakeRunsCollection:
    def __init__(self, documents=()):
        self.documents = {document["_id"]: dict(document) for document in documents}

    async def create_index(self, *_args, **_kwargs):
        return None

    async def insert_one(self, document):
        self.documents[document["_id"]] = dict(document)

    async def update_one(self, query, update):
        document = self.documents.get(query["_id"])
        if document is None or not _matches(document, {k: v for k, v in query.items() if k != "_id"}):
            return SimpleNamespace(matched_count=0)
        document.update(update["$set"])
        return SimpleNamespace(matched_count=1)

    async def find_one(self, query, **_kwargs):
        matches = [document for document in self.documents.values() if _matches(document, query)]
        return matches[0] if matches else None


class FakeLockDatabase:
    def __init__(self, *, lock=None, runs=()):
        self.collections = {
            "migration_locks": FakeLockCollection(lock),
            "migration_runs": FakeRunsCollection(runs),
        }

    def __getitem__(self, name):
        return self.collections[name]


@pytest.mark.asyncio
async def test_lock_service_reclaims_an_expired_lease_and_abandons_old_run():
    now = utcnow()
    database = FakeLockDatabase(
        lock={
            "_id": "organization-backfill",
            "run_id": "old-run",
            "expires_at": now - timedelta(seconds=1),
        },
        runs=[{"_id": "old-run", "status": "running"}],
    )
    service = MigrationLockService(database)

    await service.acquire_lock(
        migration_name="organization-backfill",
        run_id="new-run",
        dry_run=False,
        triggered_by="test",
        lease_seconds=60,
    )

    assert database["migration_locks"].document["run_id"] == "new-run"
    assert database["migration_runs"].documents["old-run"]["status"] == "abandoned"
    assert database["migration_runs"].documents["new-run"]["status"] == "running"


@pytest.mark.asyncio
async def test_lock_service_stops_a_worker_that_lost_its_lease():
    database = FakeLockDatabase()
    service = MigrationLockService(database)

    with pytest.raises(MigrationLockLostError):
        await service.renew_lock(
            migration_name="organization-backfill",
            run_id="lost-run",
            lease_seconds=60,
        )


@pytest.mark.asyncio
async def test_lock_service_removes_lease_when_run_ownership_cannot_be_recorded():
    class FailingStartRunsCollection(FakeRunsCollection):
        async def update_one(self, query, update):
            if update.get("$set", {}).get("status") == "running":
                return SimpleNamespace(matched_count=0)
            return await super().update_one(query, update)

    database = FakeLockDatabase()
    database.collections["migration_runs"] = FailingStartRunsCollection()
    service = MigrationLockService(database)

    with pytest.raises(MigrationLockError, match="could not record lock ownership"):
        await service.acquire_lock(
            migration_name="organization-backfill",
            run_id="new-run",
            dry_run=False,
            triggered_by="test",
            lease_seconds=60,
        )

    assert database["migration_locks"].document is None
    assert database["migration_runs"].documents["new-run"]["status"] == "failed"
