import asyncio
from copy import deepcopy

import pytest
from bson import ObjectId

from server.app.organizations.service import OrganizationProvisioningService
from server.app.organizations.validators import ensure_organization_collections
from server.scripts.migrations.organizations.backfill_organizations import (
    MIGRATION_NAME,
    backfill_organizations,
)


@pytest.mark.asyncio
async def test_protocol_a_reconciles_real_mongo_without_changing_existing_resources(test_db):
    user_id = ObjectId()
    await test_db.users.insert_one({"_id": user_id, "username": "ada"})
    selected_id = str(ObjectId())
    await test_db.user_sessions.insert_many([
        {"user_id": str(user_id), "session_id": "legacy"},
        {
            "user_id": str(user_id),
            "session_id": "selected",
            "active_organization_id": selected_id,
        },
    ])
    resources = {
        "quiz_attempts_v2": {"_id": ObjectId(), "user_id": str(user_id), "score": 2},
        "training_audit_events": {
            "_id": ObjectId(),
            "training_run_id": str(ObjectId()),
            "event_type": "run_closed",
            "payload": {"report_schema_version": 2, "summary": {"completed_count": 1}},
        },
        "product_events": {
            "_id": ObjectId(),
            "event_type": "quiz_generated",
            "user_id": str(user_id),
        },
    }
    for name, document in resources.items():
        await test_db[name].insert_one(deepcopy(document))

    initial_names = set(await test_db.list_collection_names())
    dry_run = await backfill_organizations(
        dry_run=True, strict=True, database_instance=test_db
    )
    assert dry_run.provisioned_users == 1
    assert set(await test_db.list_collection_names()) == initial_names
    assert "default_organization_id" not in await test_db.users.find_one({"_id": user_id})

    result = await backfill_organizations(
        dry_run=False, strict=True, database_instance=test_db
    )
    assert not result.blocked
    assert result.provisioned_users == 1
    assert result.backfilled_sessions == 1
    user = await test_db.users.find_one({"_id": user_id})
    personal = await test_db.organizations.find_one({"personal_owner_user_id": str(user_id)})
    assert personal["name"] == "ada's workspace"
    assert user["default_organization_id"] == str(personal["_id"])
    membership = await test_db.organization_memberships.find_one({"user_id": str(user_id)})
    assert (membership["role"], membership["status"]) == ("owner", "active")
    legacy = await test_db.user_sessions.find_one({"session_id": "legacy"})
    assert legacy["active_organization_id"] == user["default_organization_id"]
    selected = await test_db.user_sessions.find_one({"session_id": "selected"})
    assert selected["active_organization_id"] == selected_id

    await backfill_organizations(dry_run=False, strict=True, database_instance=test_db)
    assert await test_db.organizations.count_documents({}) == 2
    assert await test_db.organization_memberships.count_documents({}) == 1
    assert await test_db.migration_runs.count_documents({
        "migration_name": MIGRATION_NAME, "status": "completed"
    }) == 2
    for name, document in resources.items():
        assert await test_db[name].find_one({"_id": document["_id"]}) == document


@pytest.mark.asyncio
async def test_concurrent_personal_provisioning_uses_one_org_and_membership(test_db):
    await ensure_organization_collections(
        test_db, test_db.organizations, test_db.organization_memberships
    )
    user_id = ObjectId()
    await test_db.users.insert_one({"_id": user_id, "username": "ada"})
    service = OrganizationProvisioningService(
        organizations_collection=test_db.organizations,
        memberships_collection=test_db.organization_memberships,
        users_collection=test_db.users,
    )

    results = await asyncio.gather(*(
        service.ensure_personal_organization(user_id=str(user_id), organization_name="Ada")
        for _ in range(4)
    ))

    assert len({str(result["_id"]) for result in results}) == 1
    assert await test_db.organizations.count_documents({}) == 1
    assert await test_db.organization_memberships.count_documents({}) == 1
    user = await test_db.users.find_one({"_id": user_id})
    assert user["default_organization_id"] == str(results[0]["_id"])
