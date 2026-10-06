from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

from bson import ObjectId

from server.app.db.core.connection import database
from server.app.organizations.validators import ensure_organization_collections
from server.scripts.migrations.v2.migration.lock import MigrationLockService


logger = logging.getLogger(__name__)
MIGRATION_NAME = "organization_resource_scope_backfill_v1"
CLEANUP_MIGRATION_NAME = "organization_resource_unresolvable_cleanup_v1"
LOCK_LEASE_SECONDS = 900
LOCK_HEARTBEAT_SECONDS = 60
MAX_EXAMPLES = 25
RESOURCE_COLLECTIONS = (
    "quizzes_v2",
    "folders_v2",
    "saved_quizzes_v2",
    "quiz_history_v2",
    "quiz_attempts_v2",
    "ai_generated_quizzes",
    "training_runs",
    "notifications",
    "folder_items_v2",
    "training_assignments",
    "training_audit_events",
    "training_email_deliveries",
    "live_quiz_sessions",
    "live_quiz_invitations",
)

MISSING_SCOPE_QUERY = {
    "$or": [
        {"organization_id": {"$exists": False}},
        {"organization_id": None},
        # Curated seed quizzes belong to the platform library but have no
        # human author. Requiring a synthetic creator would leave every seed
        # document perpetually eligible for reconciliation.
        {
            "$and": [
                {"source": {"$ne": "seed"}},
                {
                    "$or": [
                        {"created_by_user_id": {"$exists": False}},
                        {"created_by_user_id": None},
                    ]
                },
            ]
        },
    ]
}


class ResourceBackfillBlockedError(RuntimeError):
    """Raised after a strict run durably records unresolved ownership."""

    def __init__(self, report: "ResourceBackfillReport") -> None:
        self.report = report
        super().__init__(
            f"Resource organization backfill has {report.unresolved} unresolved records"
        )


class ResourceScopeVerificationError(RuntimeError):
    """Raised when strict policy cannot safely rely on Protocol B output."""


@dataclass
class ResourceCleanupReport:
    """Audit record for removal of data with no resolvable tenant identity."""

    run_id: str
    dry_run: bool
    scanned: int = 0
    deleted: int = 0
    blocked: int = 0
    deleted_by_collection: dict[str, int] = field(default_factory=dict)
    blocked_examples: list[dict[str, str]] = field(default_factory=list)

    def record_deleted(self, collection: str, count: int = 1) -> None:
        self.deleted += count
        self.deleted_by_collection[collection] = (
            self.deleted_by_collection.get(collection, 0) + count
        )

    def record_blocked(self, record_id: Any, reason: str) -> None:
        self.blocked += 1
        if len(self.blocked_examples) < MAX_EXAMPLES:
            self.blocked_examples.append(
                {"record_id": str(record_id), "reason": reason}
            )


@dataclass
class ResourceBackfillReport:
    run_id: str
    dry_run: bool
    already_completed: bool = False
    scanned: int = 0
    updated: int = 0
    unchanged: int = 0
    unresolved: int = 0
    unresolved_examples: list[dict[str, str]] = field(default_factory=list)
    by_collection: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, collection: str, outcome: str, record_id: Any, reason: str | None = None) -> None:
        self.scanned += 1
        counts = self.by_collection.setdefault(collection, {"updated": 0, "unchanged": 0, "unresolved": 0})
        counts[outcome] += 1
        setattr(self, outcome, getattr(self, outcome) + 1)
        if outcome == "unresolved" and len(self.unresolved_examples) < MAX_EXAMPLES:
            self.unresolved_examples.append(
                {"collection": collection, "record_id": str(record_id), "reason": reason or "unresolved"}
            )


async def auto_backfill_resource_organizations(
    *,
    batch_size: int = 200,
    run_id: str | None = None,
    triggered_by: str = "auto",
    database_instance: Any | None = None,
) -> ResourceBackfillReport:
    """Run Protocol B only when the environment still has scope gaps.

    This startup-safe controller does bounded existence checks after a prior
    completion. When it finds legacy-shaped records, strict read-only
    validation must pass before the locked, idempotent writer runs.
    """
    db = database_instance if database_instance is not None else database
    lock = MigrationLockService(db)
    await lock.ensure_indexes()
    completed = await lock.get_latest_completed_run(MIGRATION_NAME)
    has_scope_gaps = await _has_missing_resource_scopes(db)

    if completed and not has_scope_gaps:
        return ResourceBackfillReport(
            run_id=run_id or str(uuid.uuid4()),
            dry_run=False,
            already_completed=True,
        )

    # The write pass validates again under its lease, so a change after this
    # preflight cannot turn the preflight report into a trust boundary.
    await backfill_resource_organizations(
        dry_run=True,
        batch_size=batch_size,
        strict=True,
        triggered_by=f"{triggered_by}:preflight",
        database_instance=db,
    )
    return await backfill_resource_organizations(
        dry_run=False,
        batch_size=batch_size,
        run_id=run_id,
        # Reconcile legacy-shaped records created while testing another branch
        # even when an earlier migration run is already marked completed.
        force=bool(completed),
        strict=True,
        triggered_by=triggered_by,
        database_instance=db,
    )


async def _has_missing_resource_scopes(db) -> bool:
    """Avoid a historical collection scan when a completed environment is clean."""
    for collection in RESOURCE_COLLECTIONS:
        missing = await db[collection].find_one(MISSING_SCOPE_QUERY, projection={"_id": 1})
        if missing is not None:
            return True
    return False


async def verify_resource_organization_scope(
    *,
    database_instance: Any | None = None,
) -> dict[str, int]:
    """Verify Protocol B completion without writing to the target database.

    This is intentionally a manual release-gate command for environments where
    resource migration is operator-controlled. It proves both that Protocol B
    completed and that no later writer introduced an unscoped resource.
    """
    db = database_instance if database_instance is not None else database
    if await _platform_organization_id(db) is None:
        raise ResourceScopeVerificationError(
            "Platform library organization is missing; complete Protocol A first"
        )

    lock = MigrationLockService(db)
    await lock.ensure_indexes()
    if not await lock.get_latest_completed_run(MIGRATION_NAME):
        raise ResourceScopeVerificationError(
            "Protocol B has no completed migration run; execute the controlled backfill first"
        )

    gaps: dict[str, int] = {}
    for collection in RESOURCE_COLLECTIONS:
        count = await db[collection].count_documents(MISSING_SCOPE_QUERY)
        if count:
            gaps[collection] = count
    if gaps:
        formatted = ", ".join(f"{collection}={count}" for collection, count in sorted(gaps.items()))
        raise ResourceScopeVerificationError(
            f"Protocol B verification found unscoped resources: {formatted}"
        )
    return {"collections_checked": len(RESOURCE_COLLECTIONS), "unscoped_records": 0}


def _is_local_compose_database(mongo_uri: str | None = None) -> bool:
    """Limit automatic destructive cleanup to the Compose Mongo service."""
    mongo_uri = mongo_uri if mongo_uri is not None else os.getenv("MONGO_URI", "")
    parsed = urlparse(mongo_uri)
    return parsed.hostname == "mongodb" and parsed.path.rstrip("/") == "/quizApp_db"


def validate_cleanup_authorization(args: argparse.Namespace, *, mongo_uri: str | None = None) -> None:
    """Reject destructive cleanup unless the operator makes its scope explicit.

    This is deliberately pure so deployment wiring and CLI behavior share the
    same guard and can be tested without connecting to MongoDB.
    """
    if args.purge_unresolvable and args.auto:
        raise ValueError("--purge-unresolvable cannot be combined with --auto")
    if args.purge_unresolvable and (args.force or args.strict):
        raise ValueError("--purge-unresolvable cannot be combined with --force or --strict")
    if args.local_only and not args.purge_unresolvable:
        raise ValueError("--local-only is only valid with --purge-unresolvable")
    if args.confirm_destructive and not args.purge_unresolvable:
        raise ValueError("--confirm-destructive is only valid with --purge-unresolvable")
    if args.auto and (args.dry_run or args.force or args.strict):
        raise ValueError("--auto cannot be combined with --dry-run, --force, or --strict")
    if getattr(args, "verify_complete", False) and any(
        (
            args.purge_unresolvable,
            args.auto,
            args.dry_run,
            args.force,
            args.strict,
        )
    ):
        raise ValueError("--verify-complete cannot be combined with migration or cleanup options")
    if args.purge_unresolvable and not args.dry_run:
        if args.local_only:
            if not _is_local_compose_database(mongo_uri):
                raise ValueError(
                    "--local-only cleanup requires mongodb://mongodb:27017/quizApp_db"
                )
        elif not args.confirm_destructive:
            raise ValueError(
                "Destructive cleanup requires --local-only or --confirm-destructive"
            )


def _identifier_variants(value: Any) -> list[Any]:
    """Match legacy references stored as either ObjectIds or strings."""
    variants = [value, str(value)]
    if isinstance(value, str) and ObjectId.is_valid(value):
        variants.append(ObjectId(value))
    return list(dict.fromkeys(variants))


async def _existing_user_ids(db, candidate_ids: list[Any]) -> set[str]:
    normalized_ids = _mongo_ids(candidate_ids)
    if not normalized_ids:
        return set()
    users = await db["users"].find(
        {"_id": {"$in": normalized_ids}}, projection={"_id": 1}
    ).to_list(length=len(normalized_ids))
    return {str(user["_id"]) for user in users}


def _first_owner_id(document: dict[str, Any]) -> Any | None:
    for field in (
        "created_by_user_id",
        "owner_user_id",
        "user_id",
        "owner_id",
        "created_by",
    ):
        if document.get(field):
            return document[field]
    return None


async def _has_valid_user_owned_reference(db, quiz_id: Any) -> str | None:
    """Return a reason to preserve a quiz that has a real user relationship.

    This is intentionally conservative. A valid user-linked library, history,
    attempt, folder, training run, or live session means the root is not safe
    to classify as disposable legacy data.
    """
    quiz_ids = _identifier_variants(quiz_id)
    direct_references = (
        ("saved_quizzes_v2", "user_id"),
        ("quiz_history_v2", "user_id"),
        ("quiz_attempts_v2", "user_id"),
        ("training_runs", "owner_user_id"),
    )
    for collection, owner_field in direct_references:
        references = await db[collection].find(
            {"quiz_id": {"$in": quiz_ids}}, projection={"_id": 1, owner_field: 1}
        ).to_list(length=None)
        if await _existing_user_ids(db, [item.get(owner_field) for item in references]):
            return f"valid_{collection}_reference"

    folder_items = await db["folder_items_v2"].find(
        {"quiz_id": {"$in": quiz_ids}}, projection={"folder_id": 1}
    ).to_list(length=None)
    folder_ids = [item.get("folder_id") for item in folder_items if item.get("folder_id")]
    if folder_ids:
        folders = await db["folders_v2"].find(
            {"_id": {"$in": _mongo_ids(folder_ids)}}, projection={"user_id": 1}
        ).to_list(length=None)
        if await _existing_user_ids(db, [folder.get("user_id") for folder in folders]):
            return "valid_folder_reference"

    sessions = await db["live_quiz_sessions"].find(
        {"quiz_id": {"$in": quiz_ids}},
        projection={
            "user_id": 1,
            "participant_user_id": 1,
            "creator_user_id": 1,
            "owner_user_id": 1,
        },
    ).to_list(length=None)
    session_user_ids = [
        value
        for session in sessions
        for value in (
            session.get("user_id"),
            session.get("participant_user_id"),
            session.get("creator_user_id"),
            session.get("owner_user_id"),
        )
        if value
    ]
    if await _existing_user_ids(db, session_user_ids):
        return "valid_live_session_reference"
    return None


async def _delete_count(collection, query: dict[str, Any], report: ResourceCleanupReport) -> None:
    if report.dry_run:
        count = await collection.count_documents(query)
    else:
        result = await collection.delete_many(query)
        count = result.deleted_count
    if count:
        report.record_deleted(collection.name, count)


async def _delete_unresolvable_quiz_dependencies(
    db, quiz_id: Any, report: ResourceCleanupReport
) -> None:
    quiz_query = {"quiz_id": {"$in": _identifier_variants(quiz_id)}}
    await _delete_count(db["saved_quizzes_v2"], quiz_query, report)
    await _delete_count(db["quiz_history_v2"], quiz_query, report)
    await _delete_count(db["quiz_attempts_v2"], quiz_query, report)
    await _delete_count(db["folder_items_v2"], quiz_query, report)
    await _delete_count(db["live_quiz_sessions"], quiz_query, report)
    await _delete_count(db["live_quiz_invitations"], quiz_query, report)

    runs = await db["training_runs"].find(
        quiz_query, projection={"_id": 1}
    ).to_list(length=None)
    run_ids = [run["_id"] for run in runs]
    if run_ids:
        run_query = {"training_run_id": {"$in": _identifier_variants(run_ids[0])}}
        # IDs are normally strings, but use one query containing every form.
        run_query = {
            "training_run_id": {
                "$in": [variant for run_id in run_ids for variant in _identifier_variants(run_id)]
            }
        }
        for collection in (
            "training_assignments",
            "training_audit_events",
            "training_email_deliveries",
        ):
            await _delete_count(db[collection], run_query, report)
        await _delete_count(db["training_runs"], {"_id": {"$in": run_ids}}, report)


async def cleanup_unresolvable_resources(
    *,
    dry_run: bool,
    batch_size: int = 200,
    run_id: str | None = None,
    triggered_by: str = "cli",
    database_instance: Any | None = None,
) -> ResourceCleanupReport:
    """Remove only private legacy roots with neither tenant nor user identity.

    This is an operator tool for historic local-development pollution, not a
    normal data-retention mechanism. It preserves all seeds and every quiz that
    can be connected to an existing user, then removes only guest-only children
    of a root that remains provably unresolvable.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least one")
    db = database_instance if database_instance is not None else database
    report = ResourceCleanupReport(run_id=run_id or str(uuid.uuid4()), dry_run=dry_run)
    lock = MigrationLockService(db)
    await lock.ensure_indexes()
    await lock.acquire_lock(
        migration_name=CLEANUP_MIGRATION_NAME,
        run_id=report.run_id,
        dry_run=dry_run,
        triggered_by=triggered_by,
        lease_seconds=LOCK_LEASE_SECONDS,
    )

    try:
        candidate_query = {
            "$and": [
                {"source": {"$ne": "seed"}},
                # An old public resource may still represent a live link. It
                # is never safe to infer that it is disposable from missing
                # authorship alone.
                {"visibility": {"$ne": "public"}},
                {"organization_id": {"$in": [None]}},
                {"owner_user_id": {"$in": [None]}},
                {"created_by_user_id": {"$in": [None]}},
                {"user_id": {"$in": [None]}},
                {"owner_id": {"$in": [None]}},
                {"created_by": {"$in": [None]}},
            ]
        }
        # `$in: [None]` deliberately matches missing fields and explicit nulls.
        # The projection keeps this destructive routine independent of quiz
        # model revisions while retaining enough context for an audit report.
        candidates = await db["quizzes_v2"].find(
            candidate_query,
            projection={"_id": 1, "source": 1, "visibility": 1},
        ).sort("_id", 1).to_list(length=None)
        for quiz in candidates:
            report.scanned += 1
            reason = await _has_valid_user_owned_reference(db, quiz["_id"])
            if reason:
                report.record_blocked(quiz["_id"], reason)
                continue
            await _delete_unresolvable_quiz_dependencies(db, quiz["_id"], report)
            await _delete_count(db["quizzes_v2"], {"_id": quiz["_id"]}, report)

        # Raw legacy documents are never rendered independently. Remove only
        # ownerless records after canonical references have been preserved or
        # removed, so a user-owned canonical quiz can never lose its source.
        raw_candidates = await db["ai_generated_quizzes"].find(
            {
                "$and": [
                    {"source": {"$ne": "seed"}},
                    {"organization_id": {"$in": [None]}},
                    {"user_id": {"$in": [None]}},
                    {"created_by_user_id": {"$in": [None]}},
                    {"owner_user_id": {"$in": [None]}},
                    {"owner_id": {"$in": [None]}},
                    {"created_by": {"$in": [None]}},
                ]
            },
            projection={"_id": 1},
        ).to_list(length=None)
        for raw_quiz in raw_candidates:
            report.scanned += 1
            canonical = await db["quizzes_v2"].find_one(
                {
                    "legacy_source_collection": "ai_generated_quizzes",
                    "legacy_quiz_id": {
                        "$in": _identifier_variants(raw_quiz["_id"])
                    },
                },
                projection={"_id": 1},
            )
            if canonical:
                # A retained canonical record owns this raw compatibility
                # source. This is expected preservation, not an unresolved
                # cleanup conflict.
                continue
            await _delete_count(db["ai_generated_quizzes"], {"_id": raw_quiz["_id"]}, report)

        await lock.release_lock(
            migration_name=CLEANUP_MIGRATION_NAME,
            run_id=report.run_id,
            status="completed",
            summary=asdict(report),
        )
        return report
    except Exception as exc:
        await lock.release_lock(
            migration_name=CLEANUP_MIGRATION_NAME,
            run_id=report.run_id,
            status="failed",
            summary=asdict(report),
            error=str(exc),
        )
        raise


async def backfill_resource_organizations(
    *,
    dry_run: bool,
    batch_size: int = 200,
    run_id: str | None = None,
    force: bool = False,
    strict: bool = False,
    triggered_by: str = "cli",
    database_instance: Any | None = None,
) -> ResourceBackfillReport:
    """Backfill tenant and authorship fields without changing access policy.

    This must run only after Protocol A has established a trustworthy default
    personal organization for every user. Ambiguous records are reported and
    left untouched; PR 3 never treats an unresolved legacy record as shared.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least one")
    # Motor database objects intentionally reject truth-value testing.
    # Use an explicit sentinel check so test and operator-injected databases
    # follow the same migration path as the process-global connection.
    db = database_instance if database_instance is not None else database
    report = ResourceBackfillReport(run_id=run_id or str(uuid.uuid4()), dry_run=dry_run)

    if not dry_run:
        await ensure_organization_collections(
            db,
            db["organizations"],
            db["organization_memberships"],
            db["organization_invitations"],
        )
    platform_organization_id = await _platform_organization_id(db)
    if platform_organization_id is None:
        raise RuntimeError("Platform library organization is missing; complete Protocol A first")

    lock = None
    if not dry_run:
        lock = MigrationLockService(db)
        await lock.ensure_indexes()
        if not force and await lock.get_latest_completed_run(MIGRATION_NAME):
            return report
        await lock.acquire_lock(
            migration_name=MIGRATION_NAME,
            run_id=report.run_id,
            dry_run=False,
            triggered_by=triggered_by,
            lease_seconds=LOCK_LEASE_SECONDS,
        )

    try:
        await _backfill_all(
            db=db,
            report=report,
            platform_organization_id=platform_organization_id,
            batch_size=batch_size,
            lock=lock,
        )
        if report.unresolved:
            if lock:
                await lock.release_lock(
                    migration_name=MIGRATION_NAME,
                    run_id=report.run_id,
                    status="blocked",
                    summary=asdict(report),
                    error="unresolved resource ownership",
                )
            if strict:
                raise ResourceBackfillBlockedError(report)
            return report
        if lock:
            await lock.release_lock(
                migration_name=MIGRATION_NAME,
                run_id=report.run_id,
                status="completed",
                summary=asdict(report),
            )
        return report
    except ResourceBackfillBlockedError:
        # The blocked outcome is already durable and must not be relabelled as
        # a failed migration just because strict mode stops the deployment.
        raise
    except Exception as exc:
        if lock:
            await lock.release_lock(
                migration_name=MIGRATION_NAME,
                run_id=report.run_id,
                status="failed",
                summary=asdict(report),
                error=str(exc),
            )
        raise


async def _platform_organization_id(db) -> str | None:
    platform = await db["organizations"].find_one(
        {"system_key": "platform_library", "status": "active"},
        projection={"_id": 1},
    )
    return str(platform["_id"]) if platform else None


def _mongo_ids(values: list[Any]) -> list[Any]:
    """Normalize valid Mongo identifiers once per bounded migration batch."""
    normalized_ids: list[ObjectId] = []
    seen: set[ObjectId] = set()
    for value in values:
        if isinstance(value, ObjectId):
            object_id = value
        elif isinstance(value, str) and ObjectId.is_valid(value):
            object_id = ObjectId(value)
        else:
            continue
        if object_id not in seen:
            seen.add(object_id)
            normalized_ids.append(object_id)
    return normalized_ids


async def _user_organizations_for_batch(db, owner_ids: list[Any]) -> dict[str, str]:
    normalized_ids = _mongo_ids(owner_ids)
    if not normalized_ids:
        return {}
    users = await db["users"].find(
        {"_id": {"$in": normalized_ids}},
        projection={"_id": 1, "default_organization_id": 1},
    ).to_list(length=len(normalized_ids))
    return {
        str(user["_id"]): user["default_organization_id"]
        for user in users
        if user.get("default_organization_id")
    }


async def _parent_scopes_for_batch(
    db,
    parent_collection: str,
    parent_ids: list[Any],
    owner_fields: tuple[str, ...],
    platform_organization_id: str | None = None,
) -> dict[str, tuple[str | None, str | None]]:
    normalized_ids = _mongo_ids(parent_ids)
    if not normalized_ids:
        return {}
    projection = {
        "_id": 1,
        "organization_id": 1,
        "created_by_user_id": 1,
        "source": 1,
        "visibility": 1,
    }
    projection.update({field: 1 for field in owner_fields})
    parents = await db[parent_collection].find(
        {"_id": {"$in": normalized_ids}}, projection=projection
    ).to_list(length=len(normalized_ids))
    parent_creators = [
        parent.get("created_by_user_id")
        or next((parent.get(field) for field in owner_fields if parent.get(field)), None)
        for parent in parents
    ]
    owner_organizations = await _user_organizations_for_batch(db, parent_creators)
    scopes: dict[str, tuple[str | None, str | None]] = {}
    for parent in parents:
        creator = parent.get("created_by_user_id") or next(
            (parent.get(field) for field in owner_fields if parent.get(field)), None
        )
        organization_id = parent.get("organization_id") or owner_organizations.get(
            str(creator)
        )
        if (
            organization_id is None
            and parent_collection == "quizzes_v2"
            and platform_organization_id is not None
        ):
            organization_id, creator = await _resolve_quiz_scope(
                db,
                parent,
                platform_organization_id,
                owner_organizations,
            )
        scopes[str(parent["_id"])] = (organization_id, str(creator) if creator else None)
    return scopes


async def _infer_private_quiz_owner_from_references(
    db, quiz_id: Any
) -> str | None:
    """Recover a legacy private quiz owner only from unambiguous user records.

    Before tenancy, private canonical quizzes were user-owned but some old
    writers omitted the root owner field while still recording the user's
    generated-history, saved-library, attempt, or training-run record. There
    were no cross-organization grants in that model. One and only one valid
    referenced user is therefore enough to restore the narrow historical
    scope; zero or multiple users is deliberately unresolved.
    """
    quiz_ids = _identifier_variants(quiz_id)
    references: list[Any] = []
    for collection, owner_field in (
        ("quiz_history_v2", "user_id"),
        ("saved_quizzes_v2", "user_id"),
        ("quiz_attempts_v2", "user_id"),
        ("training_runs", "owner_user_id"),
    ):
        documents = await db[collection].find(
            {"quiz_id": {"$in": quiz_ids}}, projection={owner_field: 1}
        ).to_list(length=None)
        references.extend(document.get(owner_field) for document in documents)
    valid_users = await _existing_user_ids(db, references)
    return next(iter(valid_users)) if len(valid_users) == 1 else None


async def _resolve_quiz_scope(
    db,
    document: dict[str, Any],
    platform_organization_id: str,
    user_organizations: dict[str, str],
) -> tuple[str | None, str | None]:
    """Resolve the narrowest defensible scope for a canonical legacy quiz."""
    owner_id = document.get("owner_user_id") or document.get("created_by_user_id")
    organization_id = document.get("organization_id") or user_organizations.get(
        str(owner_id)
    )
    if organization_id is None and document.get("source") == "seed":
        return platform_organization_id, None
    if organization_id is None and document.get("visibility") != "public":
        owner_id = await _infer_private_quiz_owner_from_references(db, document["_id"])
        organization_id = user_organizations.get(str(owner_id))
        if organization_id is None and owner_id:
            organization_id = (
                await _user_organizations_for_batch(db, [owner_id])
            ).get(owner_id)
    return organization_id, str(owner_id) if owner_id else None


async def _backfill_all(
    *,
    db,
    report: ResourceBackfillReport,
    platform_organization_id: str,
    batch_size: int,
    lock: MigrationLockService | None,
) -> None:
    last_renewal = time.monotonic()

    async def renew_if_due() -> None:
        nonlocal last_renewal
        if lock and time.monotonic() - last_renewal >= LOCK_HEARTBEAT_SECONDS:
            await lock.renew_lock(
                migration_name=MIGRATION_NAME,
                run_id=report.run_id,
                lease_seconds=LOCK_LEASE_SECONDS,
            )
            last_renewal = time.monotonic()

    async def process_owner_collection(collection: str, owner_field: str, *, seed_fallback: bool = False) -> None:
        async for documents in _iter_missing_scope_batches(
            db,
            collection,
            projection={
                "_id": 1,
                "organization_id": 1,
                owner_field: 1,
                "source": 1,
                "created_by_user_id": 1,
            },
            batch_size=batch_size,
        ):
            await renew_if_due()
            user_organizations = await _user_organizations_for_batch(
                db, [document.get(owner_field) for document in documents]
            )
            for document in documents:
                owner_id = document.get(owner_field)
                organization_id = document.get("organization_id") or user_organizations.get(
                    str(owner_id)
                )
                if organization_id is None and seed_fallback and document.get("source") == "seed":
                    organization_id = platform_organization_id
                if organization_id is None:
                    report.record(collection, "unresolved", document["_id"], f"missing_{owner_field}_organization")
                    continue
                await _apply_scope_updates(
                    db[collection],
                    document,
                    organization_id,
                    str(owner_id) if owner_id else None,
                    dry_run=report.dry_run,
                )
                report.record(collection, "updated", document["_id"])

    async for documents in _iter_missing_scope_batches(
        db,
        "quizzes_v2",
        projection={
            "_id": 1,
            "organization_id": 1,
            "owner_user_id": 1,
            "created_by_user_id": 1,
            "source": 1,
            "visibility": 1,
        },
        batch_size=batch_size,
    ):
        await renew_if_due()
        user_organizations = await _user_organizations_for_batch(
            db,
            [
                document.get("owner_user_id") or document.get("created_by_user_id")
                for document in documents
            ],
        )
        for document in documents:
            organization_id, owner_id = await _resolve_quiz_scope(
                db,
                document,
                platform_organization_id,
                user_organizations,
            )
            if organization_id is None:
                report.record(
                    "quizzes_v2", "unresolved", document["_id"], "missing_quiz_organization"
                )
                continue
            await _apply_scope_updates(
                db["quizzes_v2"],
                document,
                organization_id,
                owner_id,
                dry_run=report.dry_run,
            )
            report.record("quizzes_v2", "updated", document["_id"])

    await process_owner_collection("folders_v2", "user_id")
    await process_owner_collection("saved_quizzes_v2", "user_id")
    await process_owner_collection("quiz_history_v2", "user_id")
    await process_owner_collection("quiz_attempts_v2", "user_id")
    async for documents in _iter_missing_scope_batches(
        db,
        "ai_generated_quizzes",
        projection={
            "_id": 1,
            "organization_id": 1,
            "user_id": 1,
            "created_by_user_id": 1,
            "owner_user_id": 1,
            "source": 1,
        },
        batch_size=batch_size,
    ):
        await renew_if_due()
        user_organizations = await _user_organizations_for_batch(
            db,
            [
                document.get("user_id")
                or document.get("created_by_user_id")
                or document.get("owner_user_id")
                for document in documents
            ],
        )
        for document in documents:
            owner_id = (
                document.get("user_id")
                or document.get("created_by_user_id")
                or document.get("owner_user_id")
            )
            organization_id = document.get("organization_id") or user_organizations.get(
                str(owner_id)
            )
            if organization_id is None:
                canonical = await db["quizzes_v2"].find_one(
                    {
                        "legacy_source_collection": "ai_generated_quizzes",
                        "legacy_quiz_id": str(document["_id"]),
                    },
                    projection={
                        "_id": 1,
                        "organization_id": 1,
                        "owner_user_id": 1,
                        "created_by_user_id": 1,
                        "source": 1,
                        "visibility": 1,
                    },
                )
                if canonical:
                    organization_id, owner_id = await _resolve_quiz_scope(
                        db,
                        canonical,
                        platform_organization_id,
                        user_organizations,
                    )
            if organization_id is None:
                report.record(
                    "ai_generated_quizzes",
                    "unresolved",
                    document["_id"],
                    "missing_ai_generated_quiz_organization",
                )
                continue
            await _apply_scope_updates(
                db["ai_generated_quizzes"],
                document,
                organization_id,
                owner_id,
                dry_run=report.dry_run,
            )
            report.record("ai_generated_quizzes", "updated", document["_id"])

    await process_owner_collection("training_runs", "owner_user_id")
    await process_owner_collection("notifications", "user_id")

    await _backfill_by_parent(
        db,
        report,
        "folder_items_v2",
        "folder_id",
        "folders_v2",
        ("user_id",),
        batch_size,
        renew_if_due,
        platform_organization_id,
    )
    for collection in ("training_assignments", "training_audit_events", "training_email_deliveries"):
        await _backfill_by_parent(
            db,
            report,
            collection,
            "training_run_id",
            "training_runs",
            ("owner_user_id",),
            batch_size,
            renew_if_due,
            platform_organization_id,
        )
    for collection in ("live_quiz_sessions", "live_quiz_invitations"):
        await _backfill_by_parent(
            db,
            report,
            collection,
            "quiz_id",
            "quizzes_v2",
            ("owner_user_id",),
            batch_size,
            renew_if_due,
            platform_organization_id,
        )


async def _backfill_by_parent(
    db,
    report,
    collection: str,
    parent_field: str,
    parent_collection: str,
    parent_owner_fields: tuple[str, ...],
    batch_size: int,
    renew,
    platform_organization_id: str,
) -> None:
    async for documents in _iter_missing_scope_batches(
        db,
        collection,
        projection={"_id": 1, "organization_id": 1, parent_field: 1, "created_by_user_id": 1},
        batch_size=batch_size,
    ):
        await renew()
        parent_scopes = await _parent_scopes_for_batch(
            db,
            parent_collection,
            [document.get(parent_field) for document in documents],
            parent_owner_fields,
            platform_organization_id,
        )
        for document in documents:
            scope = parent_scopes.get(str(document.get(parent_field)))
            organization_id = document.get("organization_id") or (scope[0] if scope else None)
            if organization_id is None:
                report.record(collection, "unresolved", document["_id"], f"missing_{parent_field}_organization")
                continue
            await _apply_scope_updates(
                db[collection],
                document,
                organization_id,
                scope[1] if scope else None,
                dry_run=report.dry_run,
            )
            report.record(collection, "updated", document["_id"])


async def _apply_scope_updates(
    collection,
    document: dict,
    organization_id: str,
    created_by_user_id: str | None,
    *,
    dry_run: bool,
) -> None:
    """Fill only absent fields so concurrent writers cannot be overwritten."""
    if dry_run:
        return
    if document.get("organization_id") is None:
        await collection.update_one(
            {
                "_id": document["_id"],
                "$or": [
                    {"organization_id": {"$exists": False}},
                    {"organization_id": None},
                ],
            },
            {"$set": {"organization_id": organization_id}},
        )
    if document.get("created_by_user_id") is None:
        await collection.update_one(
            {
                "_id": document["_id"],
                "$or": [
                    {"created_by_user_id": {"$exists": False}},
                    {"created_by_user_id": None},
                ],
            },
            {"$set": {"created_by_user_id": created_by_user_id}},
        )


async def _iter_missing_scope_batches(db, collection: str, *, projection: dict, batch_size: int):
    """Yield deterministic, bounded batches of legacy scope gaps.

    A plain Mongo cursor can move unpredictably while writers are adding or
    updating records. Advancing by `_id` keeps a migration attempt bounded and
    restartable: records written after the current cursor are handled by the
    next batch or a later idempotent run, never by an unbounded live cursor.
    """
    last_id = None
    while True:
        query = MISSING_SCOPE_QUERY
        if last_id is not None:
            query = {"$and": [MISSING_SCOPE_QUERY, {"_id": {"$gt": last_id}}]}
        documents = await (
            db[collection]
            .find(query, projection=projection)
            .sort("_id", 1)
            .limit(batch_size)
            .to_list(length=batch_size)
        )
        if not documents:
            return
        yield documents
        last_id = documents[-1]["_id"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill organization scopes on tenant-owned resources")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--purge-unresolvable",
        action="store_true",
        help="Remove only documented legacy roots with no tenant or user identity.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Permit destructive cleanup only against Docker Compose's local MongoDB.",
    )
    parser.add_argument(
        "--confirm-destructive",
        action="store_true",
        help="Explicitly authorize destructive cleanup outside local Docker Compose.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run strict preflight and write only when legacy scope gaps exist.",
    )
    parser.add_argument(
        "--verify-complete",
        action="store_true",
        help="Verify a completed Protocol B run and fail if any resource remains unscoped.",
    )
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--run-id")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--triggered-by", default="cli")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    validate_cleanup_authorization(args)
    if args.purge_unresolvable:
        report = await cleanup_unresolvable_resources(
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            run_id=args.run_id,
            triggered_by=args.triggered_by,
        )
    elif args.auto:
        report = await auto_backfill_resource_organizations(
            batch_size=args.batch_size,
            run_id=args.run_id,
            triggered_by=args.triggered_by,
        )
    elif args.verify_complete:
        report = await verify_resource_organization_scope()
    else:
        report = await backfill_resource_organizations(
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            run_id=args.run_id,
            force=args.force,
            strict=args.strict,
            triggered_by=args.triggered_by,
        )
    logger.info(
        "Resource organization migration result: %s",
        report if isinstance(report, dict) else asdict(report),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except ResourceBackfillBlockedError as exc:
        logger.error(
            "Resource organization backfill is blocked pending data repair: %s",
            asdict(exc.report),
        )
        raise SystemExit(1)
    except ResourceScopeVerificationError as exc:
        logger.error("Resource organization verification failed: %s", exc)
        raise SystemExit(1)
