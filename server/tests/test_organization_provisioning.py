from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

# Organization dependencies compose the normal authenticated-user dependency,
# which loads application settings. Keep this module independently runnable in
# the same way as the authentication resolver tests.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EMAIL_SENDER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("EMAIL_HOST", "smtp.example.com")
os.environ.setdefault("EMAIL_PORT", "587")
os.environ.setdefault("SHARE_URL", "http://localhost:3000")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from server.app.organizations.dependencies import (
    get_active_organization_context,
    get_optional_active_organization_context,
)
from server.app.organizations.models import OrganizationDocument, OrganizationPrincipal
from server.app.organizations.repository import OrganizationMembershipRepository
from server.app.organizations.service import (
    OrganizationProvisioningConflictError,
    OrganizationProvisioningService,
    PersonalOrganizationMembershipInactiveError,
    personal_workspace_name,
)
from server.app.users.models import UserOut


class FakeOrganizationsCollection:
    def __init__(self):
        self.documents = {}

    async def find_one_and_update(self, query, update, *, upsert, return_document):
        user_id = query.get("personal_owner_user_id")
        document = self.documents.get(user_id)
        if document is None:
            document = {"_id": ObjectId(), **update["$setOnInsert"]}
            self.documents[user_id] = document
        document.update(update.get("$set", {}))
        return document

    async def find_one(self, query):
        for document in self.documents.values():
            if document["_id"] == query.get("_id") and document["status"] == query.get("status"):
                return document
        return None


class FakeMembershipsCollection:
    def __init__(self):
        self.documents = {}

    async def find_one_and_update(self, query, update, *, upsert, return_document):
        overlapping_fields = set(update.get("$setOnInsert", {})) & set(update.get("$set", {}))
        if overlapping_fields:
            raise AssertionError(
                f"Mongo update operators overlap on: {sorted(overlapping_fields)}"
            )
        key = (query["organization_id"], query["user_id"])
        document = self.documents.get(key)
        if document is None:
            document = {"_id": ObjectId(), **update["$setOnInsert"]}
            self.documents[key] = document
        document.update(update.get("$set", {}))
        return document

    async def find_one(self, query):
        return self.documents.get((query["organization_id"], query["user_id"]))


class FakeUsersCollection:
    def __init__(self, *, default_organization_id=None):
        self.updated = []
        self.default_organization_id = default_organization_id

    async def find_one(self, _query):
        return {"default_organization_id": self.default_organization_id}

    async def update_one(self, query, update):
        self.updated.append((query, update))
        self.default_organization_id = update["$set"]["default_organization_id"]
        return type("Result", (), {"matched_count": 1})()


@pytest.mark.asyncio
async def test_personal_organization_provisioning_is_idempotent():
    organizations = FakeOrganizationsCollection()
    memberships = FakeMembershipsCollection()
    users = FakeUsersCollection()
    user_id = str(ObjectId())
    service = OrganizationProvisioningService(
        organizations_collection=organizations,
        memberships_collection=memberships,
        users_collection=users,
    )

    first = await service.ensure_personal_organization(
        user_id=user_id,
        organization_name="Ada's workspace",
    )
    second = await service.ensure_personal_organization(
        user_id=user_id,
        organization_name="Ada's workspace",
    )

    assert first["_id"] == second["_id"]
    assert len(organizations.documents) == 1
    assert len(memberships.documents) == 1
    membership = next(iter(memberships.documents.values()))
    assert membership["role"] == "owner"
    assert membership["status"] == "active"
    assert users.updated[-1][1]["$set"]["default_organization_id"] == str(first["_id"])


@pytest.mark.asyncio
async def test_personal_provisioning_repairs_an_inactive_owner_membership():
    organizations = FakeOrganizationsCollection()
    memberships = FakeMembershipsCollection()
    users = FakeUsersCollection()
    user_id = str(ObjectId())
    service = OrganizationProvisioningService(
        organizations_collection=organizations,
        memberships_collection=memberships,
        users_collection=users,
    )
    organization = await service.ensure_personal_organization(
        user_id=user_id,
        organization_name="Ada's workspace",
    )
    membership = next(iter(memberships.documents.values()))
    membership.update({"role": "learner", "status": "suspended"})

    await service.ensure_personal_organization(
        user_id=user_id,
        organization_name="Ada's workspace",
        repair_membership=True,
    )

    assert membership["role"] == "owner"
    assert membership["status"] == "active"


@pytest.mark.asyncio
async def test_normal_personal_provisioning_does_not_reactivate_a_disabled_membership():
    organizations = FakeOrganizationsCollection()
    memberships = FakeMembershipsCollection()
    users = FakeUsersCollection()
    user_id = str(ObjectId())
    service = OrganizationProvisioningService(
        organizations_collection=organizations,
        memberships_collection=memberships,
        users_collection=users,
    )
    await service.ensure_personal_organization(
        user_id=user_id,
        organization_name="Ada's workspace",
    )
    membership = next(iter(memberships.documents.values()))
    membership.update({"role": "owner", "status": "suspended"})

    with pytest.raises(PersonalOrganizationMembershipInactiveError):
        await service.ensure_personal_organization(
            user_id=user_id,
            organization_name="Ada's workspace",
        )

    assert membership["role"] == "owner"
    assert membership["status"] == "suspended"


@pytest.mark.asyncio
async def test_personal_provisioning_rejects_a_conflicting_user_default():
    organizations = FakeOrganizationsCollection()
    memberships = FakeMembershipsCollection()
    users = FakeUsersCollection(default_organization_id="different-organization")
    service = OrganizationProvisioningService(
        organizations_collection=organizations,
        memberships_collection=memberships,
        users_collection=users,
    )

    with pytest.raises(OrganizationProvisioningConflictError):
        await service.ensure_personal_organization(
            user_id=str(ObjectId()),
            organization_name="Ada",
        )

    assert users.updated == []


@pytest.mark.asyncio
async def test_personal_provisioning_detects_a_concurrent_default_change():
    class ConcurrentUsersCollection(FakeUsersCollection):
        def __init__(self):
            super().__init__()
            self.find_calls = 0

        async def find_one(self, _query):
            self.find_calls += 1
            return {
                "default_organization_id": (
                    None if self.find_calls == 1 else "concurrent-organization"
                )
            }

        async def update_one(self, query, update):
            self.updated.append((query, update))
            return type("Result", (), {"matched_count": 0})()

    users = ConcurrentUsersCollection()
    service = OrganizationProvisioningService(
        organizations_collection=FakeOrganizationsCollection(),
        memberships_collection=FakeMembershipsCollection(),
        users_collection=users,
    )

    with pytest.raises(OrganizationProvisioningConflictError, match="changed while"):
        await service.ensure_personal_organization(
            user_id=str(ObjectId()),
            organization_name="Ada",
        )


@pytest.mark.asyncio
async def test_personal_reconciliation_requires_an_active_owner_membership():
    class QueryRecordingCollection:
        def __init__(self):
            self.query = None

        async def find_one(self, query):
            self.query = query
            return None

    collection = QueryRecordingCollection()
    await OrganizationMembershipRepository(collection).get_active_owner_membership(
        organization_id="organization-1",
        user_id="user-1",
    )

    assert collection.query == {
        "organization_id": "organization-1",
        "user_id": "user-1",
        "role": "owner",
        "status": "active",
    }


def test_organization_model_rejects_an_ownerless_personal_tenant():
    with pytest.raises(ValidationError):
        OrganizationDocument(kind="personal", name="Missing owner")


def test_personal_workspace_name_is_valid_for_unbounded_profile_values():
    assert personal_workspace_name(None) == "Personal workspace"
    assert personal_workspace_name(" " * 20) == "Personal workspace"

    workspace_name = personal_workspace_name("A" * 200)
    assert workspace_name.endswith("'s workspace")
    assert len(workspace_name) == 160


def test_platform_library_is_the_only_ownerless_personal_tenant():
    library = OrganizationDocument(
        kind="personal",
        name="Quizwerk Library",
        system_key="platform_library",
    )

    assert library.personal_owner_user_id is None


def test_organization_model_rejects_unknown_system_tenants():
    with pytest.raises(ValidationError):
        OrganizationDocument(
            kind="personal",
            name="Unexpected system tenant",
            system_key="another_system_tenant",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "corporate", "name": "Acme", "system_key": "platform_library"},
        {
            "kind": "personal",
            "name": "Ada's workspace",
            "personal_owner_user_id": "user-1",
            "system_key": "platform_library",
        },
        {
            "kind": "personal",
            "name": "Quizwerk Library",
            "created_by_user_id": "user-1",
            "system_key": "platform_library",
        },
    ],
)
def test_platform_library_identity_cannot_be_attached_to_customer_tenants(kwargs):
    with pytest.raises(ValidationError):
        OrganizationDocument(**kwargs)


class FakeSessionsCollection:
    def __init__(self, session):
        self.session = session
        self.updated = None

    async def find_one(self, query):
        expires_at = self.session["expires_at"]
        if (
            query["session_id"] == self.session["session_id"]
            and query["user_id"] == self.session["user_id"]
            and self.session["revoked_at"] is None
            and expires_at > query["expires_at"]["$gt"]
        ):
            return self.session
        return None

    async def update_one(self, query, update):
        self.updated = (query, update)
        if (
            query.get("session_id") == self.session["session_id"]
            and query.get("revoked_at") == self.session["revoked_at"]
            and query.get("active_organization_id") == self.session.get("active_organization_id")
        ):
            self.session.update(update["$set"])
            return type("Result", (), {"matched_count": 1})()
        return type("Result", (), {"matched_count": 0})()


def _user(default_organization_id: str) -> UserOut:
    return UserOut(
        id=str(ObjectId()),
        username="ada",
        email="ada@example.com",
        is_active=True,
        is_verified=True,
        status="active",
        default_organization_id=default_organization_id,
    )


@pytest.mark.asyncio
async def test_active_context_falls_back_to_default_and_proves_membership():
    organization_id = str(ObjectId())
    user = _user(organization_id)
    principal = OrganizationPrincipal(user_id=user.id, session_id="session-1")
    sessions = FakeSessionsCollection(
        {
            "session_id": "session-1",
            "user_id": user.id,
            "revoked_at": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "active_organization_id": None,
        }
    )
    organizations = FakeOrganizationsCollection()
    organizations.documents["owner"] = {
        "_id": ObjectId(organization_id),
        "kind": "personal",
        "status": "active",
    }
    memberships = FakeMembershipsCollection()
    memberships.documents[(organization_id, user.id)] = {
        "organization_id": organization_id,
        "user_id": user.id,
        "role": "owner",
        "status": "active",
    }

    context = await get_active_organization_context(
        principal=principal,
        current_user=user,
        sessions_collection=sessions,
        organizations_collection=organizations,
        memberships_collection=memberships,
    )

    assert context.organization_id == organization_id
    assert context.membership_role == "owner"
    assert sessions.updated[1]["$set"]["active_organization_id"] == organization_id


@pytest.mark.asyncio
async def test_active_context_recovers_a_stale_session_selector_to_valid_default():
    default_organization_id = str(ObjectId())
    stale_organization_id = str(ObjectId())
    user = _user(default_organization_id)
    principal = OrganizationPrincipal(user_id=user.id, session_id="session-1")
    sessions = FakeSessionsCollection(
        {
            "session_id": "session-1",
            "user_id": user.id,
            "revoked_at": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "active_organization_id": stale_organization_id,
        }
    )
    organizations = FakeOrganizationsCollection()
    organizations.documents["default"] = {
        "_id": ObjectId(default_organization_id),
        "kind": "personal",
        "status": "active",
    }
    memberships = FakeMembershipsCollection()
    memberships.documents[(default_organization_id, user.id)] = {
        "organization_id": default_organization_id,
        "user_id": user.id,
        "role": "owner",
        "status": "active",
    }

    context = await get_active_organization_context(
        principal=principal,
        current_user=user,
        sessions_collection=sessions,
        organizations_collection=organizations,
        memberships_collection=memberships,
    )

    assert context.organization_id == default_organization_id
    assert context.active_scope_recovered is True
    assert sessions.updated[1]["$set"]["active_organization_id"] == default_organization_id


@pytest.mark.asyncio
async def test_active_context_rejects_a_concurrent_scope_switch_during_fallback():
    default_organization_id = str(ObjectId())
    stale_organization_id = str(ObjectId())
    user = _user(default_organization_id)
    principal = OrganizationPrincipal(user_id=user.id, session_id="session-1")

    class ConcurrentSwitchSessions(FakeSessionsCollection):
        async def update_one(self, query, update):
            self.updated = (query, update)
            self.session["active_organization_id"] = "newly-selected-organization"
            return type("Result", (), {"matched_count": 0})()

    sessions = ConcurrentSwitchSessions(
        {
            "session_id": "session-1",
            "user_id": user.id,
            "revoked_at": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "active_organization_id": stale_organization_id,
        }
    )
    organizations = FakeOrganizationsCollection()
    organizations.documents["default"] = {
        "_id": ObjectId(default_organization_id),
        "kind": "personal",
        "status": "active",
    }
    memberships = FakeMembershipsCollection()
    memberships.documents[(default_organization_id, user.id)] = {
        "organization_id": default_organization_id,
        "user_id": user.id,
        "role": "owner",
        "status": "active",
    }

    with pytest.raises(HTTPException) as exc_info:
        await get_active_organization_context(
            principal=principal,
            current_user=user,
            sessions_collection=sessions,
            organizations_collection=organizations,
            memberships_collection=memberships,
        )

    assert exc_info.value.status_code == 409
    assert sessions.session["active_organization_id"] == "newly-selected-organization"


@pytest.mark.asyncio
async def test_active_context_denies_a_user_without_membership():
    organization_id = str(ObjectId())
    user = _user(organization_id)
    principal = OrganizationPrincipal(user_id=user.id, session_id="session-1")
    sessions = FakeSessionsCollection(
        {
            "session_id": "session-1",
            "user_id": user.id,
            "revoked_at": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "active_organization_id": organization_id,
        }
    )
    organizations = FakeOrganizationsCollection()
    organizations.documents["owner"] = {
        "_id": ObjectId(organization_id),
        "kind": "corporate",
        "status": "active",
    }

    with pytest.raises(HTTPException) as exc:
        await get_active_organization_context(
            principal=principal,
            current_user=user,
            sessions_collection=sessions,
            organizations_collection=organizations,
            memberships_collection=FakeMembershipsCollection(),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_optional_context_treats_an_identity_without_session_scope_as_anonymous():
    assert await get_optional_active_organization_context(
        current_user=SimpleNamespace(session_id=None),
        sessions_collection=object(),
        organizations_collection=object(),
        memberships_collection=object(),
    ) is None


@pytest.mark.asyncio
async def test_optional_context_degrades_removed_or_unprovisioned_identity_to_guest(monkeypatch):
    import server.app.organizations.dependencies as organization_dependencies

    async def no_active_tenant(**_kwargs):
        raise HTTPException(status_code=403, detail="Organization access denied")

    monkeypatch.setattr(
        organization_dependencies,
        "resolve_active_organization_context",
        no_active_tenant,
    )

    assert await get_optional_active_organization_context(
        current_user=SimpleNamespace(
            id="user-1",
            session_id="session-1",
            role="user",
        ),
        sessions_collection=object(),
        organizations_collection=object(),
        memberships_collection=object(),
    ) is None
