from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from server.app.cohorts.models import CohortDocument, CohortMembershipDocument
from server.app.cohorts.repository import CohortRepository
from server.app.cohorts.schemas import CreateCohortRequest, SetCohortMemberRequest, UpdateCohortRequest
from server.app.cohorts.service import CohortService
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.policy import OrganizationAction, OrganizationPolicy


def matches(row, query):
    for key, value in query.items():
        actual = row.get(key)
        if isinstance(value, dict):
            if "$in" in value and actual not in value["$in"]:
                return False
            if "$ne" in value and actual == value["$ne"]:
                return False
        elif actual != value:
            return False
    return True


class Cursor:
    def __init__(self, rows):
        self.rows = deepcopy(rows)

    async def to_list(self, length):
        return self.rows[:length] if length is not None else self.rows


class Collection:
    name = "test_collection"

    def __init__(self, rows=None):
        self.rows = rows or []
        self.queries = []

    async def find_one(self, query, *args):
        self.queries.append(query)
        return next((deepcopy(row) for row in self.rows if matches(row, query)), None)

    def find(self, query, *args):
        self.queries.append(query)
        return Cursor([row for row in self.rows if matches(row, query)])


class MemoryRepository:
    def __init__(self):
        self.rows = {}
        self.memberships = Collection()
        self.lock = asyncio.Lock()

    @asynccontextmanager
    async def hierarchy_mutation(self, organization_id):
        async with self.lock:
            yield "lease-token"

    async def get(self, organization_id, cohort_id):
        await asyncio.sleep(0)
        cohort_id = str(ObjectId(cohort_id)) if ObjectId.is_valid(cohort_id) else cohort_id
        row = self.rows.get(cohort_id)
        return deepcopy(row) if row and row["organization_id"] == organization_id else None

    async def has_active_children(self, organization_id, cohort_id):
        await asyncio.sleep(0)
        return any(row["organization_id"] == organization_id and row.get("parent_cohort_id") == cohort_id
                   and row["status"] == "active" for row in self.rows.values())

    async def has_children(self, organization_id, cohort_id):
        return any(row["organization_id"] == organization_id and row.get("parent_cohort_id") == cohort_id
                   for row in self.rows.values())

    async def create(self, document, *, token):
        row = document.model_dump(by_alias=True)
        self.rows[str(row["_id"])] = deepcopy(row)
        return row

    async def update(self, organization_id, cohort_id, changes, *, token):
        row = self.rows[cohort_id]
        assert row["organization_id"] == organization_id
        row.update(changes)
        return deepcopy(row)

    async def get_membership(self, organization_id, cohort_id, user_id):
        return await self.memberships.find_one({
            "organization_id": organization_id, "cohort_id": cohort_id,
            "user_id": user_id, "status": "active",
        })

    async def set_member(self, document, *, token):
        row = document.model_dump(by_alias=True)
        self.memberships.rows = [existing for existing in self.memberships.rows if not all(
            existing[key] == row[key] for key in ("organization_id", "cohort_id", "user_id")
        )]
        self.memberships.rows.append(deepcopy(row))
        return row

    async def remove_member(self, organization_id, cohort_id, user_id, *, token):
        for row in self.memberships.rows:
            if row["organization_id"] == organization_id and row["cohort_id"] == cohort_id and row["user_id"] == user_id:
                row["status"] = "removed"

    async def snapshot_member_rows(self, organization_id, cohort_id, *, limit, organization_memberships_collection):
        active_ids = {row["user_id"] for row in organization_memberships_collection.rows
                      if row["organization_id"] == organization_id and row["status"] == "active"}
        return deepcopy([row for row in self.memberships.rows if
                         row["organization_id"] == organization_id and row["cohort_id"] == cohort_id
                         and row["role"] == "member" and row["status"] == "active"
                         and row["user_id"] in active_ids][:limit + 1])


@pytest.fixture
def world():
    organization_id, user_id = str(ObjectId()), str(ObjectId())
    context = OrganizationContext(
        organization_id=organization_id, organization_kind="school", membership_role="owner",
        principal=OrganizationPrincipal(user_id=user_id, session_id="session"),
        membership={"role": "owner", "status": "active"},
    )
    repository = MemoryRepository()
    memberships = Collection([{
        "organization_id": organization_id, "user_id": user_id, "role": "owner", "status": "active",
    }])
    users = Collection([{"_id": ObjectId(user_id), "username": "owner", "email": "owner@example.test"}])
    return SimpleNamespace(service=CohortService(repository, memberships, users), context=context,
                           repository=repository, memberships=memberships, users=users)


async def create(world, name="Class", parent=None):
    return await world.service.create_cohort(CreateCohortRequest(
        name=name, kind="class", parent_cohort_id=parent,
    ), world.context)


def add_user(world, *, role="learner", status="active"):
    user_id = str(ObjectId())
    world.memberships.rows.append({"organization_id": world.context.organization_id,
                                   "user_id": user_id, "role": role, "status": status})
    world.users.rows.append({"_id": ObjectId(user_id), "username": "member", "email": f"{user_id}@example.test"})
    return user_id


def context_for(world, user_id):
    membership = next(row for row in world.memberships.rows if row["user_id"] == user_id)
    return world.context.model_copy(update={
        "principal": OrganizationPrincipal(user_id=user_id, session_id="member-session"),
        "membership_role": membership["role"], "membership": deepcopy(membership),
    })


@pytest.mark.asyncio
async def test_create_normalizes_name_and_admin_only_crud(world):
    cohort = await create(world, "  Science   class  ")
    assert cohort.name == "Science class"
    assert cohort.organization_id == world.context.organization_id
    assert cohort.can_manage and cohort.can_assign and cohort.can_report
    learner = context_for(world, add_user(world))
    with pytest.raises(HTTPException) as exc:
        await world.service.create_cohort(CreateCohortRequest(name="No", kind="team"), learner)
    assert exc.value.status_code == 403
    changed = await world.service.update_cohort(cohort.id, UpdateCohortRequest(name="Updated"), world.context)
    assert changed.name == "Updated"


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get", "update", "archive", "set_member", "remove_member", "policy_resource"])
async def test_foreign_cohort_returns_404_for_every_resource_operation(world, operation):
    cohort = await create(world)
    world.repository.rows[cohort.id]["organization_id"] = str(ObjectId())
    calls = {
        "get": lambda: world.service.get_cohort(cohort.id, world.context),
        "update": lambda: world.service.update_cohort(cohort.id, UpdateCohortRequest(name="No"), world.context),
        "archive": lambda: world.service.archive_cohort(cohort.id, world.context),
        "set_member": lambda: world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=world.context.principal.user_id), world.context),
        "remove_member": lambda: world.service.remove_member(cohort.id, world.context.principal.user_id, world.context),
        "policy_resource": lambda: world.service.policy_resource(cohort.id, world.context),
    }
    with pytest.raises(HTTPException) as exc:
        await calls[operation]()
    assert exc.value.status_code == 404
    assert world.repository.rows[cohort.id]["name"] == "Class"


@pytest.mark.asyncio
async def test_in_tenant_nonmember_denied_and_malformed_id_hidden(world):
    cohort = await create(world)
    with pytest.raises(HTTPException) as exc:
        await world.service.get_cohort(cohort.id, context_for(world, add_user(world)))
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        await world.service.get_cohort("not-an-objectid", world.context)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_missing_or_forbidden_resource_is_checked_before_busy_hierarchy_lock(world):
    cohort = await create(world)

    @asynccontextmanager
    async def busy(_organization_id):
        raise HTTPException(409, "busy")
        yield

    world.repository.hierarchy_mutation = busy
    with pytest.raises(HTTPException) as exc:
        await world.service.update_cohort(str(ObjectId()), UpdateCohortRequest(name="No"), world.context)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        await world.service.archive_cohort(cohort.id, context_for(world, add_user(world)))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_hierarchy_rejects_foreign_parent_grandchild_cycle_and_archived_parent(world):
    root = await create(world, "Root")
    child = await create(world, "Child", root.id)
    for parent, target in [(child.id, root.id), (root.id, root.id)]:
        with pytest.raises(HTTPException) as exc:
            await world.service.update_cohort(target, UpdateCohortRequest(parent_cohort_id=parent), world.context)
        assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        await create(world, "Grandchild", child.id)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        await world.service.archive_cohort(root.id, world.context)
    assert exc.value.status_code == 409
    await world.service.archive_cohort(child.id, world.context)
    await world.service.archive_cohort(root.id, world.context)
    with pytest.raises(HTTPException) as exc:
        await create(world, "No", root.id)
    assert exc.value.status_code == 409
    foreign_id = str(ObjectId())
    with pytest.raises(HTTPException) as exc:
        await create(world, "Foreign", foreign_id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_opposing_reparents_cannot_form_cycle(world):
    first, second = await create(world, "First"), await create(world, "Second")
    results = await asyncio.gather(
        world.service.update_cohort(first.id, UpdateCohortRequest(parent_cohort_id=second.id), world.context),
        world.service.update_cohort(second.id, UpdateCohortRequest(parent_cohort_id=first.id), world.context),
        return_exceptions=True,
    )
    assert sum(isinstance(result, HTTPException) for result in results) == 1
    assert sum(row.get("parent_cohort_id") is not None for row in world.repository.rows.values()) == 1


@pytest.mark.asyncio
async def test_archived_children_do_not_allow_a_retained_three_level_hierarchy(world):
    root, other = await create(world, "Root"), await create(world, "Other")
    child = await create(world, "Child", root.id)
    await world.service.archive_cohort(child.id, world.context)
    with pytest.raises(HTTPException) as exc:
        await world.service.update_cohort(root.id, UpdateCohortRequest(parent_cohort_id=other.id), world.context)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_uppercase_identifiers_cannot_bypass_self_parent_check_or_member_removal(world):
    cohort = await create(world)
    with pytest.raises(HTTPException) as exc:
        await world.service.update_cohort(cohort.id.upper(), UpdateCohortRequest(parent_cohort_id=cohort.id), world.context)
    assert exc.value.status_code == 409
    user_id = add_user(world)
    await world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=user_id), world.context)
    assert len(await world.service.snapshot_active_members(cohort.id.upper(), world.context)) == 1
    await world.service.remove_member(cohort.id.upper(), user_id.upper(), world.context)
    assert await world.service.snapshot_active_members(cohort.id, world.context) == []


@pytest.mark.asyncio
async def test_child_creation_racing_parent_move_never_creates_three_levels(world):
    first, second = await create(world, "First"), await create(world, "Second")
    results = await asyncio.gather(
        create(world, "Child", first.id),
        world.service.update_cohort(first.id, UpdateCohortRequest(parent_cohort_id=second.id), world.context),
        return_exceptions=True,
    )
    assert sum(isinstance(result, HTTPException) for result in results) == 1
    for row in world.repository.rows.values():
        if row.get("parent_cohort_id"):
            assert world.repository.rows[row["parent_cohort_id"]].get("parent_cohort_id") is None


@pytest.mark.asyncio
async def test_members_require_active_org_membership_and_names_never_expose_email(world):
    cohort = await create(world)
    user_id = add_user(world)
    member = await world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=user_id), world.context)
    assert member.name == "member"
    assert "email" not in member.model_dump()
    world.memberships.rows[-1]["status"] = "suspended"
    with pytest.raises(HTTPException) as exc:
        await world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=user_id), world.context)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_facilitator_delegation_independent_of_org_role_and_flags(world):
    cohort = await create(world)
    user_id = add_user(world, role="learner")
    await world.service.set_member(cohort.id, SetCohortMemberRequest(
        user_id=user_id, role="facilitator", can_assign=True, can_report=False,
    ), world.context)
    context = context_for(world, user_id)
    assert await world.service.can(context, cohort.id, "assign")
    assert not await world.service.can(context, cohort.id, "report")
    assert not await world.service.can(context, cohort.id, "manage")
    await world.service.set_member(cohort.id, SetCohortMemberRequest(
        user_id=user_id, role="facilitator", can_assign=False, can_report=True,
    ), world.context)
    assert not await world.service.can(context, cohort.id, "assign")
    assert await world.service.can(context, cohort.id, "report")
    assert await world.service.can(context, cohort.id, "attempt")
    await world.service.remove_member(cohort.id, user_id, world.context)
    assert not await world.service.can(context, cohort.id, "report")


@pytest.mark.asyncio
async def test_archiving_does_not_prevent_closing_or_reporting_existing_assignments(world):
    cohort = await create(world)
    user_id = add_user(world)
    await world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=user_id, role="facilitator"), world.context)
    delegate = context_for(world, user_id)
    await world.service.archive_cohort(cohort.id, world.context)
    assert not await world.service.can_for_cohort(cohort.id, delegate, OrganizationAction.ASSIGNMENT_CREATE)
    assert await world.service.can_for_cohort(cohort.id, delegate, OrganizationAction.ASSIGNMENT_MANAGE)
    assert await world.service.can(delegate, cohort.id, "report")
    with pytest.raises(HTTPException) as exc:
        await world.service.snapshot_active_members(cohort.id, delegate)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_guardian_membership_does_not_grant_any_learner_attempt_access(world):
    cohort = await create(world)
    user_id = add_user(world, role="guardian")
    await world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=user_id, role="guardian"), world.context)
    guardian = context_for(world, user_id)
    assert (await world.service.get_cohort(cohort.id, guardian)).id == cohort.id
    for capability in ("assign", "report", "attempt", "manage"):
        assert not await world.service.can(guardian, cohort.id, capability)


@pytest.mark.asyncio
async def test_revoked_org_membership_and_stale_admin_role_do_not_authorize(world):
    cohort = await create(world)
    world.memberships.rows[0]["role"] = "learner"
    assert not await world.service.can_for_cohort(cohort.id, world.context, OrganizationAction.COHORT_MANAGE)
    world.memberships.rows[0]["status"] = "suspended"
    assert not await world.service.can_for_cohort(cohort.id, world.context, OrganizationAction.COHORT_READ)
    with pytest.raises(HTTPException) as exc:
        await world.service.get_cohort(cohort.id, world.context)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_snapshot_only_active_member_role_and_does_not_inherit_children(world):
    root = await create(world)
    child = await create(world, "Child", root.id)
    member = add_user(world)
    await world.service.set_member(root.id, SetCohortMemberRequest(user_id=member), world.context)
    for role in ("facilitator", "guardian"):
        await world.service.set_member(root.id, SetCohortMemberRequest(user_id=add_user(world), role=role), world.context)
    await world.service.set_member(child.id, SetCohortMemberRequest(user_id=add_user(world)), world.context)
    inactive = add_user(world)
    await world.service.set_member(root.id, SetCohortMemberRequest(user_id=inactive), world.context)
    world.memberships.rows[-1]["status"] = "removed"
    recipients = await world.service.snapshot_active_members(root.id, world.context)
    assert [row["user_id"] for row in recipients] == [member]
    await world.service.remove_member(root.id, member, world.context)
    assert recipients[0]["user_id"] == member
    assert await world.service.snapshot_active_members(root.id, world.context) == []


@pytest.mark.asyncio
async def test_snapshot_rejects_overflow_and_limit_cannot_be_raised(world):
    cohort = await create(world)
    world.repository.snapshot_member_rows = AsyncMock(return_value=[{"user_id": str(ObjectId())}] * 1001)
    with pytest.raises(HTTPException) as exc:
        await world.service.snapshot_active_members(cohort.id, world.context)
    assert exc.value.status_code == 413
    with pytest.raises(HTTPException) as exc:
        await world.service.snapshot_active_members(cohort.id, world.context, limit=1001)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_can_for_cohort_does_not_swallow_database_errors(world):
    cohort = await create(world)
    world.repository.get = AsyncMock(side_effect=RuntimeError("database offline"))
    with pytest.raises(RuntimeError, match="database offline"):
        await world.service.can_for_cohort(cohort.id, world.context, OrganizationAction.COHORT_READ)


@pytest.mark.asyncio
async def test_accessible_ids_use_scoped_delegation_and_reject_overflow(world):
    cohort = await create(world)
    user_id = add_user(world)
    context = context_for(world, user_id)
    membership = {"organization_id": context.organization_id, "cohort_id": cohort.id,
                  "user_id": user_id, "role": "facilitator", "status": "active",
                  "can_assign": False, "can_report": True}
    row = {**world.repository.rows[cohort.id], "_membership": [membership]}
    pipelines = []

    def aggregate(pipeline):
        pipelines.append(pipeline)
        return Cursor([row])

    world.repository.cohorts = SimpleNamespace(aggregate=aggregate)
    assert await world.service.scoped_accessible_ids(context, OrganizationAction.COHORT_REPORT) == [cohort.id]
    lookup_match = pipelines[0][2]["$lookup"]["pipeline"][0]["$match"]
    assert lookup_match["organization_id"] == context.organization_id
    assert lookup_match["user_id"] == user_id
    assert lookup_match["can_report"] is True
    assert "can_assign" not in lookup_match
    world.repository.cohorts.aggregate = lambda pipeline: Cursor([row] * 1001)
    with pytest.raises(HTTPException) as exc:
        await world.service.scoped_accessible_ids(context, OrganizationAction.COHORT_REPORT)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_cohort_list_is_paged_and_bulk_loads_delegation(world):
    cohort = await create(world)
    user_id = add_user(world)
    await world.service.set_member(cohort.id, SetCohortMemberRequest(user_id=user_id), world.context)
    context = context_for(world, user_id)
    world.repository.list_page = AsyncMock(return_value=([world.repository.rows[cohort.id]], "next-cursor"))
    page = await world.service.list_cohorts(context, limit=10)
    assert page.items[0].id == cohort.id
    assert page.next_cursor == "next-cursor"
    assert world.repository.list_page.await_args.kwargs["user_id"] == user_id
    assert world.repository.list_page.await_args.args == (context.organization_id,)


@pytest.mark.asyncio
async def test_member_options_are_admin_only_and_omit_emails(world):
    user_id = add_user(world)
    with pytest.raises(HTTPException) as exc:
        await world.service.member_options(context_for(world, user_id))
    assert exc.value.status_code == 403
    rows = [{"_id": ObjectId(), "user_id": user_id, "_user": [{"username": "Learner"}]}]
    world.memberships.aggregate = lambda pipeline: Cursor(rows)
    page = await world.service.member_options(world.context, limit=10)
    assert page.items[0].model_dump() == {"user_id": user_id, "name": "Learner"}


@pytest.mark.parametrize("role", ["owner", "admin", "author", "facilitator", "learner", "guardian", "auditor"])
@pytest.mark.parametrize("can_assign,can_report", [(False, False), (True, False), (False, True), (True, True)])
def test_policy_delegation_matrix(role, can_assign, can_report):
    user_id, organization_id, cohort_id = str(ObjectId()), str(ObjectId()), str(ObjectId())
    principal = OrganizationPrincipal(user_id=user_id, session_id="session")
    context = OrganizationContext(organization_id=organization_id, organization_kind="school",
                                  membership_role=role, principal=principal, membership={"status": "active"})
    resource = {"organization_id": organization_id, "cohort_id": cohort_id, "status": "active",
                "cohort_membership": {"organization_id": organization_id, "cohort_id": cohort_id,
                "user_id": user_id, "role": "facilitator", "status": "active",
                "can_assign": can_assign, "can_report": can_report}}
    policy = OrganizationPolicy()
    assert policy.can(principal, OrganizationAction.ASSIGNMENT_CREATE, resource, context) is (role in {"owner", "admin"} or can_assign)
    assert policy.can(principal, OrganizationAction.COHORT_REPORT, resource, context) is (role in {"owner", "admin", "auditor"} or can_report)
    assert policy.can(principal, OrganizationAction.MEMBER_ATTEMPT_READ, resource, context) is (role in {"owner", "admin", "auditor"} or can_report)
    assert policy.can(principal, OrganizationAction.COHORT_MEMBERSHIP_MANAGE, resource, context) is (role in {"owner", "admin"})
    resource["cohort_membership"]["cohort_id"] = str(ObjectId())
    if role not in {"owner", "admin", "auditor"}:
        assert not policy.can(principal, OrganizationAction.COHORT_REPORT, resource, context)
    resource["organization_id"] = str(ObjectId())
    assert not policy.can(principal, OrganizationAction.COHORT_READ, resource, context)


@pytest.mark.parametrize("action", [OrganizationAction.COHORT_REPORT, OrganizationAction.MEMBER_ATTEMPT_READ])
def test_direct_recipient_facilitator_reporting_stays_creator_scoped(action):
    user_id, organization_id = str(ObjectId()), str(ObjectId())
    principal = OrganizationPrincipal(user_id=user_id, session_id="session")
    context = OrganizationContext(organization_id=organization_id, organization_kind="school",
                                  membership_role="facilitator", principal=principal, membership={"status": "active"})
    resource = {"organization_id": organization_id, "created_by_user_id": user_id}
    policy = OrganizationPolicy()
    assert policy.can(principal, action, resource, context)
    resource["created_by_user_id"] = str(ObjectId())
    assert not policy.can(principal, action, resource, context)
    resource["created_by_user_id"] = user_id
    resource["cohort_id"] = str(ObjectId())
    assert not policy.can(principal, action, resource, context)


def test_new_cohort_permissions_require_active_org_membership_even_for_owner():
    principal = OrganizationPrincipal(user_id=str(ObjectId()), session_id="session")
    context = OrganizationContext(organization_id=str(ObjectId()), organization_kind="school",
        membership_role="owner", principal=principal, membership={"status": "suspended"})
    resource = {"organization_id": context.organization_id}
    for action in (OrganizationAction.COHORT_READ, OrganizationAction.COHORT_MANAGE,
                   OrganizationAction.ASSIGNMENT_CREATE, OrganizationAction.COHORT_REPORT):
        assert not OrganizationPolicy().can(principal, action, resource, context)


@pytest.mark.parametrize("payload", [
    {"name": "   ", "kind": "class"}, {"name": "x", "kind": "unknown"},
    {"name": "x", "kind": "class", "organization_id": str(ObjectId())},
    {"name": "x", "kind": "class", "parent_cohort_id": "bad-id"},
])
def test_invalid_or_client_scoped_cohort_payloads_are_rejected(payload):
    with pytest.raises(ValidationError):
        CreateCohortRequest(**payload)


def test_facilitator_defaults_and_nonfacilitator_escalation_validation():
    request = SetCohortMemberRequest(user_id=str(ObjectId()), role="facilitator")
    assert request.can_assign and request.can_report
    request = SetCohortMemberRequest(user_id=str(ObjectId()))
    assert not request.can_assign and not request.can_report
    with pytest.raises(ValidationError):
        SetCohortMemberRequest(user_id=str(ObjectId()), role="guardian", can_report=True)
    with pytest.raises(ValidationError):
        SetCohortMemberRequest(user_id=str(ObjectId()), role="facilitator", can_report=None)
    with pytest.raises(ValidationError):
        UpdateCohortRequest(name=None)
    with pytest.raises(ValidationError):
        CohortMembershipDocument(organization_id=str(ObjectId()), cohort_id=str(ObjectId()),
            user_id=str(ObjectId()), created_by_user_id=str(ObjectId()), role="member", can_report=True)


@pytest.mark.asyncio
async def test_real_repository_queries_are_organization_scoped_and_invalid_ids_do_not_query():
    cohorts, members, locks = Collection(), Collection(), Collection()
    repository = CohortRepository(cohorts, members, locks)
    assert await repository.get("org", "bad-id") is None
    assert cohorts.queries == []
    cohort_id = str(ObjectId())
    await repository.get("org", cohort_id)
    await repository.has_active_children("org", cohort_id)
    await repository.get_membership("org", cohort_id, "user")
    assert all(query["organization_id"] == "org" for query in cohorts.queries + members.queries)


@pytest.mark.asyncio
async def test_hierarchy_busy_lease_fails_before_writing():
    locks = SimpleNamespace(find_one_and_update=AsyncMock(side_effect=DuplicateKeyError("busy")))
    repository = CohortRepository(Collection(), Collection(), locks)
    with pytest.raises(HTTPException) as exc:
        async with repository.hierarchy_mutation(str(ObjectId())):
            pytest.fail("a busy lease must not enter the critical section")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_hierarchy_lost_lease_cannot_write_and_release_is_token_scoped():
    locks = SimpleNamespace(
        find_one_and_update=AsyncMock(return_value={"token": "claimed"}),
        find_one=AsyncMock(return_value=None), update_one=AsyncMock(),
    )
    collection = SimpleNamespace(insert_one=AsyncMock())
    repository = CohortRepository(collection, Collection(), locks)
    organization_id = str(ObjectId())
    async with repository.hierarchy_mutation(organization_id) as token:
        with pytest.raises(HTTPException) as exc:
            await repository.create(CohortDocument(organization_id=organization_id,
                created_by_user_id=str(ObjectId()), kind="team", name="Team"), token=token)
        assert exc.value.status_code == 409
    collection.insert_one.assert_not_awaited()
    query = locks.update_one.await_args.args[0]
    assert query == {"_id": organization_id, "token": token}


@pytest.fixture
def api(world, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("JWT_SECRET", "cohort-route-test-secret")
    monkeypatch.setenv("EMAIL_HOST", "smtp.example.test")
    monkeypatch.setenv("EMAIL_PORT", "587")
    monkeypatch.setenv("SENDER_EMAIL", "sender@example.test")
    monkeypatch.setenv("SENDER_PASSWORD", "test-password")
    monkeypatch.setenv("SHARE_URL", "http://localhost:3000")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from server.app.cohorts import routes
    from server.app.core.dependencies import get_verified_user
    from server.app.organizations.dependencies import get_active_organization_context

    monkeypatch.setattr(routes.limiter, "enabled", False)
    app = FastAPI()
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[routes.get_cohort_service] = lambda: world.service
    app.dependency_overrides[get_active_organization_context] = lambda: world.context
    app.dependency_overrides[get_verified_user] = lambda: SimpleNamespace(is_verified=True)
    with TestClient(app) as client:
        yield client, app


def test_http_cohort_crud_member_routes_and_tenant_errors(api, world):
    client, _app = api
    result = client.post("/api/cohorts", json={"kind": "class", "name": "Class"})
    assert result.status_code == 201, result.text
    cohort_id = result.json()["id"]
    user_id = add_user(world)
    result = client.post(f"/api/cohorts/{cohort_id}/members", json={"user_id": user_id})
    assert result.status_code == 200, result.text
    assert "email" not in result.json()
    result = client.patch(f"/api/cohorts/{cohort_id}", json={"name": "Updated"})
    assert result.status_code == 200, result.text
    assert result.json()["name"] == "Updated"
    result = client.delete(f"/api/cohorts/{cohort_id}/members/{user_id}")
    assert result.status_code == 204, result.text
    assert result.content == b""
    assert client.get("/api/cohorts/not-an-objectid").status_code == 404
    world.repository.rows[cohort_id]["organization_id"] = str(ObjectId())
    for method, suffix, body in [
        ("get", "", None), ("patch", "", {"name": "Foreign"}), ("delete", "", None),
        ("post", "/members", {"user_id": user_id}), ("get", "/members", None),
    ]:
        response = client.request(method, f"/api/cohorts/{cohort_id}{suffix}", json=body)
        assert response.status_code == 404, response.text


def test_http_unverified_user_cannot_mutate(api, world):
    from server.app.core.dependencies import get_verified_user

    client, app = api

    def reject_unverified():
        raise HTTPException(403, "Email not verified")

    app.dependency_overrides[get_verified_user] = reject_unverified
    result = client.post("/api/cohorts", json={"kind": "class", "name": "No"})
    assert result.status_code == 403
    assert world.repository.rows == {}


def test_http_member_options_is_static_route_and_rejects_invalid_pagination(api, world):
    client, _app = api
    world.memberships.aggregate = lambda pipeline: Cursor([])
    result = client.get("/api/cohorts/member-options")
    assert result.status_code == 200, result.text
    assert result.json() == {"items": [], "next_cursor": None}
    assert client.get("/api/cohorts/member-options?limit=101").status_code == 422
    assert client.get("/api/cohorts/member-options?cursor=invalid").status_code == 422
    assert client.post("/api/cohorts", json={"kind": "class", "name": "No", "organization_id": str(ObjectId())}).status_code == 422
