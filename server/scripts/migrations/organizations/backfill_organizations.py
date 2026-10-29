from __future__ import annotations

import argparse
import asyncio
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from server.app.db.core.connection import database
from server.app.organizations.repository import OrganizationRepository
from server.app.organizations.invitation_service import OrganizationLifecycleService
from server.app.organizations.service import OrganizationProvisioningService
from server.app.organizations.validators import ensure_organization_collections
from server.scripts.migrations.v2.migration.lock import (
    MigrationLockError,
    MigrationLockService,
)


logger = logging.getLogger(__name__)
# Versioned so an environment that completed v1 runs the additive session
# reconciliation introduced in this revision exactly once on deployment.
MIGRATION_NAME = "organization_personal_tenant_backfill_v2"
LOCK_LEASE_SECONDS = 900
LOCK_HEARTBEAT_SECONDS = 60
LOCK_ACQUIRE_MAX_ATTEMPTS = 5
LOCK_ACQUIRE_INITIAL_RETRY_SECONDS = 5
MAX_UNRESOLVED_EXAMPLES = 25


class OrganizationBackfillBlockedError(RuntimeError):
    """Raised only when an explicit strict reconciliation cannot complete."""


@dataclass
class OrganizationBackfillReport:
    run_id: str
    dry_run: bool
    already_completed: bool = False
    already_blocked: bool = False
    blocked: bool = False
    scanned_users: int = 0
    provisioned_users: int = 0
    reconciled_users: int = 0
    skipped_users: int = 0
    backfilled_sessions: int = 0
    reconciled_shared_organizations: int = 0
    platform_library_created: bool = False
    unresolved_count: int = 0
    unresolved_examples: list[dict[str, str]] = field(default_factory=list)

    def add_unresolved(self, *, record_id: str, reason: str) -> None:
        self.unresolved_count += 1
        if len(self.unresolved_examples) < MAX_UNRESOLVED_EXAMPLES:
            self.unresolved_examples.append({"record_id": record_id, "reason": reason})


async def backfill_organizations(
    *,
    dry_run: bool,
    batch_size: int = 200,
    limit: int | None = None,
    run_id: str | None = None,
    force: bool = False,
    strict: bool = False,
    triggered_by: str = "cli",
    database_instance: Any | None = None,
) -> OrganizationBackfillReport:
    """Provision personal tenants before organization-scope enforcement.

    ``--dry-run`` is intentionally read-only. The deployment path uses write
    mode, where schema setup, locking, and completion recording are required.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least one")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least one when provided")

    db = database_instance if database_instance is not None else database
    run_id = run_id or str(uuid.uuid4())
    report = OrganizationBackfillReport(run_id=run_id, dry_run=dry_run)

    if dry_run:
        await _reconcile_users(
            db=db,
            report=report,
            batch_size=batch_size,
            limit=limit,
            write=False,
            lock_service=None,
        )
        report.blocked = report.unresolved_count > 0
        _raise_if_unresolved(report, strict=strict)
        return report

    # Pre-deploy execution happens before FastAPI startup. Establish only the
    # additive organization contract required for this migration before writes.
    await ensure_organization_collections(
        db,
        db["organizations"],
        db["organization_memberships"],
    )
    lock_service = MigrationLockService(db)
    await lock_service.ensure_indexes()

    reconcile_missing_defaults_only = False
    completed_before_lock = False
    if not force:
        terminal_run = await lock_service.get_latest_terminal_run(MIGRATION_NAME)
        if terminal_run and terminal_run["status"] == "completed":
            # A rolling deploy can create a legacy user after the original
            # cursor passed. Reconcile only users still missing a default on
            # later deploys instead of repeating a full historical scan.
            reconcile_missing_defaults_only = True
            completed_before_lock = True
        elif terminal_run and terminal_run["status"] == "blocked":
            _restore_blocked_report(report, terminal_run)
            _raise_if_unresolved(report, strict=strict)
            reconcile_missing_defaults_only = True

    await _acquire_lock_with_retry(
        lock_service=lock_service,
        run_id=run_id,
        triggered_by=triggered_by,
    )
    try:
        # Another deployment may have completed after this process checked
        # state but before it acquired the lease.
        if not force:
            terminal_run = await lock_service.get_latest_terminal_run(MIGRATION_NAME)
            if (
                terminal_run is not None
                and terminal_run["status"] == "completed"
                and not completed_before_lock
            ):
                report.already_completed = True
                await lock_service.release_lock(
                    migration_name=MIGRATION_NAME,
                    run_id=run_id,
                    status="skipped",
                    summary=asdict(report),
                )
                return report

        # Reconcile every unambiguous identity even when historical conflicts
        # exist. A conflict is recorded for operator repair, not allowed to
        # deny healthy users the tenant invariant during this additive phase.
        await _reconcile_users(
            db=db,
            report=report,
            batch_size=batch_size,
            limit=limit,
            write=True,
            lock_service=lock_service,
            only_missing_default=reconcile_missing_defaults_only,
        )
        if report.unresolved_count:
            report.blocked = True
            await lock_service.release_lock(
                migration_name=MIGRATION_NAME,
                run_id=run_id,
                status="blocked",
                summary=asdict(report),
                error=_unresolved_error_message(report),
            )
            _raise_if_unresolved(report, strict=strict)
            return report

        # A bounded run is diagnostic/reconciliation work, not evidence that
        # every existing identity has a tenant. Never use it as the gate.
        status = "partial" if limit is not None else "completed"
        await lock_service.release_lock(
            migration_name=MIGRATION_NAME,
            run_id=run_id,
            status=status,
            summary=asdict(report),
        )
        return report
    except OrganizationBackfillBlockedError:
        # The durable run is already marked blocked. Do not overwrite that
        # operational state as a runtime migration failure.
        raise
    except Exception as exc:
        await lock_service.release_lock(
            migration_name=MIGRATION_NAME,
            run_id=run_id,
            status="failed",
            summary=asdict(report),
            error=str(exc),
        )
        raise


async def _reconcile_users(
    *,
    db,
    report: OrganizationBackfillReport,
    batch_size: int,
    limit: int | None,
    write: bool,
    lock_service: MigrationLockService | None,
    only_missing_default: bool = False,
) -> None:
    organizations = OrganizationRepository(db["organizations"])
    provisioning = OrganizationProvisioningService(
        organizations_collection=db["organizations"],
        memberships_collection=db["organization_memberships"],
        users_collection=db["users"],
    )

    if write:
        lifecycle = OrganizationLifecycleService(
            organizations_collection=db["organizations"],
            memberships_collection=db["organization_memberships"],
            users_collection=db["users"],
        )
        try:
            reconciled, unresolved_shared = await lifecycle.reconcile_provisioning_shared_organizations()
            report.reconciled_shared_organizations += reconciled
            for organization_id in unresolved_shared:
                report.add_unresolved(
                    record_id=organization_id,
                    reason="shared_organization_provisioning_could_not_be_reconciled",
                )
        except Exception:
            logger.exception("Unable to reconcile provisioning shared organizations")
            report.add_unresolved(
                record_id="shared_organization_provisioning",
                reason="shared_organization_provisioning_reconciliation_failed",
            )

    platform_library = await db["organizations"].find_one(
        {"system_key": "platform_library"}
    )
    if platform_library is None:
        report.platform_library_created = True
        if write:
            await organizations.ensure_platform_library_organization()
    elif not _is_active_platform_library(platform_library):
        report.add_unresolved(
            record_id="platform_library",
            reason="platform_library_is_not_an_active_ownerless_personal_organization",
        )

    processed = 0
    last_id = None
    last_heartbeat = time.monotonic()

    async def renew_if_due(*, force: bool = False) -> None:
        nonlocal last_heartbeat
        if lock_service is None:
            return
        if force or time.monotonic() - last_heartbeat >= LOCK_HEARTBEAT_SECONDS:
            await lock_service.renew_lock(
                migration_name=MIGRATION_NAME,
                run_id=report.run_id,
                lease_seconds=LOCK_LEASE_SECONDS,
            )
            last_heartbeat = time.monotonic()

    while limit is None or processed < limit:
        missing_default_query = {
            "$or": [
                {"default_organization_id": {"$exists": False}},
                {"default_organization_id": None},
            ]
        }
        if only_missing_default and last_id is not None:
            query = {"$and": [missing_default_query, {"_id": {"$gt": last_id}}]}
        elif only_missing_default:
            query = missing_default_query
        elif last_id is not None:
            query = {"_id": {"$gt": last_id}}
        else:
            query = {}
        remaining = batch_size if limit is None else min(batch_size, limit - processed)
        users = await db["users"].find(query).sort("_id", 1).limit(remaining).to_list(remaining)
        if not users:
            break

        user_ids = [str(user["_id"]) for user in users]
        personal_organizations = await db["organizations"].find(
            {"kind": "personal", "personal_owner_user_id": {"$in": user_ids}}
        ).to_list(length=len(user_ids))
        organizations_by_owner = {
            organization["personal_owner_user_id"]: organization
            for organization in personal_organizations
        }
        organization_ids = [str(organization["_id"]) for organization in personal_organizations]
        active_owner_memberships: set[tuple[str, str]] = set()
        if organization_ids:
            membership_documents = await db["organization_memberships"].find(
                {
                    "organization_id": {"$in": organization_ids},
                    "user_id": {"$in": user_ids},
                    "role": "owner",
                    "status": "active",
                }
            ).to_list(length=len(organization_ids))
            active_owner_memberships = {
                (membership["organization_id"], membership["user_id"])
                for membership in membership_documents
            }

        for user in users:
            await renew_if_due()
            processed += 1
            report.scanned_users += 1
            last_id = user["_id"]
            user_id = str(user["_id"])
            personal_organization = organizations_by_owner.get(user_id)
            expected_organization_id = (
                str(personal_organization["_id"]) if personal_organization else None
            )

            if personal_organization and personal_organization.get("status") != "active":
                report.add_unresolved(
                    record_id=user_id,
                    reason="personal_organization_is_not_active",
                )
                continue
            if user.get("default_organization_id") not in {None, expected_organization_id}:
                report.add_unresolved(
                    record_id=user_id,
                    reason="default_organization_does_not_match_personal_organization",
                )
                continue

            has_matching_default = user.get("default_organization_id") == expected_organization_id
            has_active_owner_membership = (
                expected_organization_id is not None
                and (expected_organization_id, user_id) in active_owner_memberships
            )
            if has_matching_default and has_active_owner_membership:
                if write:
                    report.backfilled_sessions += await _backfill_missing_session_organizations(
                        db=db,
                        user_id=user_id,
                        organization_id=expected_organization_id,
                    )
                report.skipped_users += 1
                continue

            if not write:
                report.provisioned_users += 1
                continue

            organization = await provisioning.ensure_personal_organization(
                user_id=user_id,
                organization_name=user.get("full_name") or user.get("username"),
                repair_membership=True,
            )
            report.backfilled_sessions += await _backfill_missing_session_organizations(
                db=db,
                user_id=user_id,
                organization_id=str(organization["_id"]),
            )
            if personal_organization is None:
                report.provisioned_users += 1
            else:
                report.reconciled_users += 1

        await renew_if_due(force=True)


async def _acquire_lock_with_retry(
    *,
    lock_service: MigrationLockService,
    run_id: str,
    triggered_by: str,
) -> None:
    """Absorb brief overlapping deploys without weakening the deployment gate."""
    for attempt in range(LOCK_ACQUIRE_MAX_ATTEMPTS):
        try:
            await lock_service.acquire_lock(
                migration_name=MIGRATION_NAME,
                run_id=run_id,
                dry_run=False,
                triggered_by=triggered_by,
                lease_seconds=LOCK_LEASE_SECONDS,
            )
            return
        except MigrationLockError:
            if attempt == LOCK_ACQUIRE_MAX_ATTEMPTS - 1:
                raise
            delay_seconds = LOCK_ACQUIRE_INITIAL_RETRY_SECONDS * (2**attempt)
            logger.warning(
                "Organization migration lock is held; retrying in %s seconds (%s/%s)",
                delay_seconds,
                attempt + 1,
                LOCK_ACQUIRE_MAX_ATTEMPTS,
            )
            await asyncio.sleep(delay_seconds)


async def _backfill_missing_session_organizations(*, db, user_id: str, organization_id: str | None) -> int:
    """Set legacy session scope only when a session has not selected one yet."""

    if organization_id is None:
        return 0
    result = await db["user_sessions"].update_many(
        {
            "user_id": user_id,
            "$or": [
                {"active_organization_id": {"$exists": False}},
                {"active_organization_id": None},
            ],
        },
        {"$set": {"active_organization_id": organization_id}},
    )
    return result.modified_count


def _is_active_platform_library(organization: dict[str, Any]) -> bool:
    return (
        organization.get("kind") == "personal"
        and organization.get("status") == "active"
        and "personal_owner_user_id" in organization
        and "created_by_user_id" in organization
        and organization.get("personal_owner_user_id") is None
        and organization.get("created_by_user_id") is None
        and organization.get("system_key") == "platform_library"
    )


def _restore_blocked_report(
    report: OrganizationBackfillReport, blocked_run: dict[str, Any]
) -> None:
    """Avoid rescanning on every additive deployment until an operator retries."""
    summary = blocked_run.get("summary") or {}
    report.already_blocked = True
    report.blocked = True
    report.unresolved_count = int(summary.get("unresolved_count", 0))
    examples = summary.get("unresolved_examples") or []
    report.unresolved_examples = [
        example
        for example in examples[:MAX_UNRESOLVED_EXAMPLES]
        if isinstance(example, dict)
        and isinstance(example.get("record_id"), str)
        and isinstance(example.get("reason"), str)
    ]


def _unresolved_error_message(report: OrganizationBackfillReport) -> str:
    examples = ", ".join(
        f"{item['record_id']} ({item['reason']})"
        for item in report.unresolved_examples
    )
    return (
        "Organization backfill found unresolved tenant records "
        f"({report.unresolved_count} total): {examples}"
    )


def _raise_if_unresolved(
    report: OrganizationBackfillReport, *, strict: bool
) -> None:
    if report.unresolved_count and strict:
        raise OrganizationBackfillBlockedError(_unresolved_error_message(report))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision organization tenants for existing users")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rerun a completed or blocked migration for deliberate reconciliation.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when historical tenant conflicts remain unresolved.",
    )
    parser.add_argument(
        "--triggered-by",
        default="cli",
        help="Execution source recorded in the migration audit trail.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    report = await backfill_organizations(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        limit=args.limit,
        run_id=args.run_id,
        force=args.force,
        strict=args.strict,
        triggered_by=args.triggered_by,
    )
    if report.blocked:
        logger.warning("Organization backfill is blocked pending data repair: %s", asdict(report))
    else:
        logger.info("Organization backfill complete: %s", asdict(report))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
