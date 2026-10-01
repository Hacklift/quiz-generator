from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from server.scripts.migrations.organizations.backfill_resource_organizations import (
    auto_backfill_resource_organizations,
    backfill_resource_organizations,
    cleanup_unresolvable_resources,
    ResourceBackfillBlockedError,
    validate_cleanup_authorization,
)


def _cleanup_args(**overrides):
    values = {
        "purge_unresolvable": True,
        "auto": False,
        "force": False,
        "strict": False,
        "local_only": False,
        "confirm_destructive": False,
        "dry_run": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_destructive_cleanup_requires_an_explicit_nonlocal_confirmation():
    with pytest.raises(ValueError, match="Destructive cleanup requires"):
        validate_cleanup_authorization(
            _cleanup_args(),
            mongo_uri="mongodb+srv://production.example/quizApp_db",
        )


def test_local_only_cleanup_rejects_any_non_compose_database():
    with pytest.raises(ValueError, match="local-only cleanup requires"):
        validate_cleanup_authorization(
            _cleanup_args(local_only=True),
            mongo_uri="mongodb://localhost:27017/quizApp_db",
        )


def test_production_deployment_paths_never_invoke_destructive_resource_cleanup():
    repository_root = Path(__file__).resolve().parents[3]
    for relative_path in ("docker-compose.prod.yml", "deploy/deploy.sh", "render.yaml"):
        contents = (repository_root / relative_path).read_text(encoding="utf-8")
        assert "tenancy-resource-cleanup" not in contents
        assert "--purge-unresolvable" not in contents


@pytest.mark.asyncio
async def test_resource_backfill_scopes_user_records_and_platform_seed_content(test_db):
    now = datetime.now(timezone.utc)
    user_id = ObjectId()
    personal_organization_id = ObjectId()
    platform_organization_id = ObjectId()

    await test_db["users"].insert_one(
        {"_id": user_id, "default_organization_id": str(personal_organization_id)}
    )
    await test_db["organizations"].insert_many(
        [
            {
                "_id": personal_organization_id,
                "kind": "personal",
                "name": "Ada's workspace",
                "status": "active",
                "settings": {},
                "personal_owner_user_id": str(user_id),
                "system_key": None,
                "created_by_user_id": str(user_id),
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": platform_organization_id,
                "kind": "personal",
                "name": "Quizwerk Library",
                "status": "active",
                "settings": {},
                "personal_owner_user_id": None,
                "system_key": "platform_library",
                "created_by_user_id": None,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    folder_id = ObjectId()
    training_run_id = ObjectId()
    quiz_session_id = ObjectId()
    quiz_invitation_id = ObjectId()
    assignment_id = ObjectId()
    audit_event_id = ObjectId()
    delivery_id = ObjectId()
    saved_quiz_id = ObjectId()
    generated_quiz_id = ObjectId()
    attempt_id = ObjectId()
    notification_id = ObjectId()
    await test_db["quizzes_v2"].insert_many(
        [
            {"_id": ObjectId(), "owner_user_id": str(user_id), "source": "manual"},
            {"_id": ObjectId(), "owner_user_id": None, "source": "seed"},
        ]
    )
    inferred_quiz_id = ObjectId()
    inferred_raw_quiz_id = ObjectId()
    await test_db["quizzes_v2"].insert_one(
        {
            "_id": inferred_quiz_id,
            "source": "ai",
            "visibility": "private",
            "legacy_source_collection": "ai_generated_quizzes",
            "legacy_quiz_id": str(inferred_raw_quiz_id),
        }
    )
    await test_db["folders_v2"].insert_one({"_id": folder_id, "user_id": str(user_id)})
    await test_db["folder_items_v2"].insert_one({"_id": ObjectId(), "folder_id": str(folder_id)})
    await test_db["saved_quizzes_v2"].insert_one({"_id": saved_quiz_id, "user_id": str(user_id)})
    await test_db["quiz_attempts_v2"].insert_one({"_id": attempt_id, "user_id": str(user_id)})
    await test_db["ai_generated_quizzes"].insert_one({"_id": generated_quiz_id, "user_id": str(user_id)})
    await test_db["ai_generated_quizzes"].insert_one({"_id": inferred_raw_quiz_id})
    await test_db["notifications"].insert_one({"_id": notification_id, "user_id": str(user_id)})
    await test_db["training_runs"].insert_one(
        {"_id": training_run_id, "owner_user_id": str(user_id)}
    )
    await test_db["training_assignments"].insert_one(
        {"_id": assignment_id, "training_run_id": str(training_run_id)}
    )
    await test_db["training_audit_events"].insert_one(
        {"_id": audit_event_id, "training_run_id": str(training_run_id)}
    )
    await test_db["training_email_deliveries"].insert_one(
        {"_id": delivery_id, "training_run_id": str(training_run_id)}
    )
    user_quiz_id = (await test_db["quizzes_v2"].find_one({"owner_user_id": str(user_id)}))["_id"]
    await test_db["live_quiz_sessions"].insert_one(
        {"_id": quiz_session_id, "quiz_id": str(user_quiz_id)}
    )
    inferred_session_id = ObjectId()
    await test_db["live_quiz_sessions"].insert_one(
        {"_id": inferred_session_id, "quiz_id": str(inferred_quiz_id), "guest_id": "guest-1"}
    )
    await test_db["live_quiz_invitations"].insert_one(
        {"_id": quiz_invitation_id, "quiz_id": str(user_quiz_id)}
    )
    scoped_history_id = ObjectId()
    await test_db["quiz_history_v2"].insert_one(
        {
            "_id": scoped_history_id,
            "user_id": str(user_id),
            "organization_id": str(personal_organization_id),
        }
    )
    await test_db["quiz_history_v2"].insert_one(
        {
            "_id": ObjectId(),
            "user_id": str(user_id),
            "quiz_id": str(inferred_quiz_id),
            "action": "generated",
        }
    )

    preflight_report = await backfill_resource_organizations(
        dry_run=True,
        batch_size=1,
        strict=True,
        triggered_by="test-preflight",
        database_instance=test_db,
    )
    assert preflight_report.unresolved == 0

    report = await backfill_resource_organizations(
        dry_run=False,
        batch_size=1,
        force=True,
        triggered_by="test",
        database_instance=test_db,
    )

    assert report.unresolved == 0
    user_quiz = await test_db["quizzes_v2"].find_one({"owner_user_id": str(user_id)})
    seed_quiz = await test_db["quizzes_v2"].find_one({"source": "seed"})
    folder = await test_db["folders_v2"].find_one({"_id": folder_id})
    item = await test_db["folder_items_v2"].find_one({"folder_id": str(folder_id)})
    scoped_history = await test_db["quiz_history_v2"].find_one({"_id": scoped_history_id})
    inferred_quiz = await test_db["quizzes_v2"].find_one({"_id": inferred_quiz_id})
    inferred_raw_quiz = await test_db["ai_generated_quizzes"].find_one({"_id": inferred_raw_quiz_id})
    inferred_session = await test_db["live_quiz_sessions"].find_one({"_id": inferred_session_id})
    scoped_documents = [
        await test_db[collection].find_one({"_id": record_id})
        for collection, record_id in (
            ("saved_quizzes_v2", saved_quiz_id),
            ("quiz_attempts_v2", attempt_id),
            ("ai_generated_quizzes", generated_quiz_id),
            ("notifications", notification_id),
            ("training_runs", training_run_id),
            ("training_assignments", assignment_id),
            ("training_audit_events", audit_event_id),
            ("training_email_deliveries", delivery_id),
            ("live_quiz_sessions", quiz_session_id),
            ("live_quiz_invitations", quiz_invitation_id),
        )
    ]
    assert user_quiz["organization_id"] == str(personal_organization_id)
    assert user_quiz["created_by_user_id"] == str(user_id)
    assert seed_quiz["organization_id"] == str(platform_organization_id)
    assert seed_quiz.get("created_by_user_id") is None
    assert folder["organization_id"] == str(personal_organization_id)
    assert item["organization_id"] == str(personal_organization_id)
    assert scoped_history["created_by_user_id"] == str(user_id)
    assert inferred_quiz["organization_id"] == str(personal_organization_id)
    assert inferred_quiz["created_by_user_id"] == str(user_id)
    assert inferred_raw_quiz["organization_id"] == str(personal_organization_id)
    assert inferred_raw_quiz["created_by_user_id"] == str(user_id)
    assert inferred_session["organization_id"] == str(personal_organization_id)
    assert inferred_session["created_by_user_id"] == str(user_id)
    assert all(
        document["organization_id"] == str(personal_organization_id)
        and document["created_by_user_id"] == str(user_id)
        for document in scoped_documents
    )

    completed_report = await auto_backfill_resource_organizations(
        database_instance=test_db,
        triggered_by="test-auto",
    )
    assert completed_report.already_completed is True

    late_notification_id = ObjectId()
    await test_db["notifications"].insert_one(
        {"_id": late_notification_id, "user_id": str(user_id)}
    )
    reconciled_report = await auto_backfill_resource_organizations(
        database_instance=test_db,
        triggered_by="test-auto",
    )
    late_notification = await test_db["notifications"].find_one({"_id": late_notification_id})
    assert reconciled_report.updated == 1
    assert late_notification["organization_id"] == str(personal_organization_id)
    assert late_notification["created_by_user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_cleanup_only_removes_unresolvable_private_roots_and_guest_dependents(test_db):
    """A valid user reference or public root must always win over cleanup."""
    valid_user_id = ObjectId()
    orphan_quiz_id = ObjectId()
    retained_quiz_id = ObjectId()
    public_quiz_id = ObjectId()
    raw_orphan_id = ObjectId()
    raw_retained_id = ObjectId()

    await test_db["users"].insert_one({"_id": valid_user_id})
    await test_db["quizzes_v2"].insert_many(
        [
            {
                "_id": orphan_quiz_id,
                "source": "ai",
                "visibility": "private",
                "legacy_source_collection": "ai_generated_quizzes",
                "legacy_quiz_id": str(raw_orphan_id),
            },
            {
                "_id": retained_quiz_id,
                "source": "legacy",
                "visibility": "private",
                "legacy_source_collection": "ai_generated_quizzes",
                "legacy_quiz_id": str(raw_retained_id),
            },
            {
                "_id": public_quiz_id,
                "source": "legacy",
                "visibility": "public",
            },
        ]
    )
    await test_db["saved_quizzes_v2"].insert_many(
        [
            {"_id": ObjectId(), "quiz_id": str(orphan_quiz_id), "user_id": "unknown-user"},
            {"_id": ObjectId(), "quiz_id": str(retained_quiz_id), "user_id": str(valid_user_id)},
        ]
    )
    await test_db["live_quiz_sessions"].insert_many(
        [
            {"_id": ObjectId(), "quiz_id": str(orphan_quiz_id), "guest_id": "guest-only"},
            {"_id": ObjectId(), "quiz_id": str(public_quiz_id), "guest_id": "guest-public"},
        ]
    )
    await test_db["live_quiz_invitations"].insert_one(
        {"_id": ObjectId(), "quiz_id": str(orphan_quiz_id)}
    )
    await test_db["ai_generated_quizzes"].insert_many(
        [
            {"_id": raw_orphan_id, "source": "ai"},
            {"_id": raw_retained_id, "source": "ai"},
        ]
    )

    dry_report = await cleanup_unresolvable_resources(
        dry_run=True,
        triggered_by="test-dry-run",
        database_instance=test_db,
    )
    assert dry_report.deleted >= 4
    assert dry_report.blocked == 1
    assert await test_db["quizzes_v2"].count_documents({}) == 3

    report = await cleanup_unresolvable_resources(
        dry_run=False,
        triggered_by="test-write",
        database_instance=test_db,
    )
    assert report.blocked == 1
    assert await test_db["quizzes_v2"].find_one({"_id": orphan_quiz_id}) is None
    assert await test_db["ai_generated_quizzes"].find_one({"_id": raw_orphan_id}) is None
    assert await test_db["saved_quizzes_v2"].find_one({"quiz_id": str(orphan_quiz_id)}) is None
    assert await test_db["live_quiz_sessions"].find_one({"quiz_id": str(orphan_quiz_id)}) is None
    assert await test_db["live_quiz_invitations"].find_one({"quiz_id": str(orphan_quiz_id)}) is None

    assert await test_db["quizzes_v2"].find_one({"_id": retained_quiz_id}) is not None
    assert await test_db["ai_generated_quizzes"].find_one({"_id": raw_retained_id}) is not None
    assert await test_db["quizzes_v2"].find_one({"_id": public_quiz_id}) is not None
    assert await test_db["live_quiz_sessions"].find_one({"quiz_id": str(public_quiz_id)}) is not None


@pytest.mark.asyncio
async def test_backfill_does_not_guess_an_owner_when_private_quiz_references_conflict(test_db):
    now = datetime.now(timezone.utc)
    first_user_id = ObjectId()
    second_user_id = ObjectId()
    first_organization_id = ObjectId()
    second_organization_id = ObjectId()
    platform_organization_id = ObjectId()
    ambiguous_quiz_id = ObjectId()

    await test_db["users"].insert_many(
        [
            {"_id": first_user_id, "default_organization_id": str(first_organization_id)},
            {"_id": second_user_id, "default_organization_id": str(second_organization_id)},
        ]
    )
    await test_db["organizations"].insert_many(
        [
            {
                "_id": first_organization_id,
                "kind": "personal",
                "name": "First workspace",
                "status": "active",
                "settings": {},
                "personal_owner_user_id": str(first_user_id),
                "system_key": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": second_organization_id,
                "kind": "personal",
                "name": "Second workspace",
                "status": "active",
                "settings": {},
                "personal_owner_user_id": str(second_user_id),
                "system_key": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": platform_organization_id,
                "kind": "personal",
                "name": "Quizwerk Library",
                "status": "active",
                "settings": {},
                "personal_owner_user_id": None,
                "system_key": "platform_library",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    await test_db["quizzes_v2"].insert_one(
        {"_id": ambiguous_quiz_id, "source": "ai", "visibility": "private"}
    )
    await test_db["saved_quizzes_v2"].insert_many(
        [
            {"_id": ObjectId(), "quiz_id": str(ambiguous_quiz_id), "user_id": str(first_user_id)},
            {"_id": ObjectId(), "quiz_id": str(ambiguous_quiz_id), "user_id": str(second_user_id)},
        ]
    )

    with pytest.raises(ResourceBackfillBlockedError) as error:
        await backfill_resource_organizations(
            dry_run=True,
            strict=True,
            triggered_by="test-ambiguous-owner",
            database_instance=test_db,
        )

    assert error.value.report.unresolved == 1
    assert error.value.report.unresolved_examples[0]["collection"] == "quizzes_v2"
