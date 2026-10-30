from unittest.mock import AsyncMock

import pytest
from pymongo.errors import OperationFailure

from server.app.cohorts.validators import (
    _ensure_validator, cohort_membership_validator, cohort_validator, ensure_cohort_collections,
)


@pytest.mark.asyncio
async def test_concurrent_collection_creation_reapplies_validator():
    class Database:
        command = AsyncMock(side_effect=[OperationFailure("missing", code=26), None])
        create_collection = AsyncMock(side_effect=OperationFailure("exists", code=48))

    database = Database()
    validator = cohort_validator()
    await _ensure_validator(database, "cohorts", validator)
    assert database.command.await_count == 2
    assert database.command.await_args.args[0]["validator"] == validator


@pytest.mark.asyncio
async def test_validator_setup_does_not_mask_permission_or_database_failures():
    class Database:
        command = AsyncMock(side_effect=OperationFailure("denied", code=13))
        create_collection = AsyncMock()

    with pytest.raises(OperationFailure):
        await _ensure_validator(Database(), "cohorts", cohort_validator())
    Database.create_collection.assert_not_awaited()


@pytest.mark.asyncio
async def test_cohort_indexes_are_tenant_first_and_membership_is_unique():
    class Database:
        command = AsyncMock()

        def __init__(self):
            self.collections = {}

        def __getitem__(self, key):
            if key not in self.collections:
                self.collections[key] = type("Collection", (), {"create_index": AsyncMock()})()
            return self.collections[key]

    database = Database()
    await ensure_cohort_collections(database)
    for collection in database.collections.values():
        for call in collection.create_index.await_args_list:
            assert call.args[0][0][0] == "organization_id"
    unique = next(call for call in database["cohort_memberships"].create_index.await_args_list if call.kwargs.get("unique"))
    assert unique.args[0] == [("organization_id", 1), ("cohort_id", 1), ("user_id", 1)]
    assert database.command.await_count == 3


def test_mongo_membership_validator_rejects_nonfacilitator_delegation():
    validator = cohort_membership_validator()
    assert validator["$and"][1] == {"$or": [
        {"role": "facilitator"}, {"can_assign": False, "can_report": False},
    ]}
    for name in ("can_assign", "can_report"):
        assert validator["$and"][0]["$jsonSchema"]["properties"][name] == {"bsonType": "bool"}
