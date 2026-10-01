from __future__ import annotations

import os
import inspect
from datetime import datetime, timezone
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
from fastapi import HTTPException
from pydantic import ValidationError

from server.app.organizations.invitation_service import (
    OrganizationInvitationService,
    OrganizationLifecycleService,
)
from server.app.organizations.models import OrganizationInvitationDocument
from server.app.core.dependencies import get_verified_user
from server.app.organizations import routes as organization_routes
from server.app.organizations.repository import (
    InvitationMembershipStateError,
    OrganizationInvitationRepository,
    OrganizationMembershipRepository,
)
from server.app.organizations.schemas import (
    CreateOrganizationRequest,
    UpdateOrganizationMembershipRequest,
)


class RecordingCollection:
    def __init__(self):
        self.query = None
        self.update = None
        self.calls = []

    async def find_one_and_update(self, query, update, **_kwargs):
        self.query = query
        self.update = update
        self.calls.append((query, update))
        return None


@pytest.mark.asyncio
async def test_invitation_claim_binds_the_one_time_token_to_the_invited_email():
    collection = RecordingCollection()
    repository = OrganizationInvitationRepository(collection)
    now = datetime.now(timezone.utc)

    await repository.claim_token(
        token_hash="a" * 64,
        email_normalized="member@example.com",
        accepted_by_user_id="user-1",
        claim_id="claim-1",
        now=now,
    )

    assert collection.calls[0][0] == {
        "token_hash": "a" * 64,
        "email_normalized": "member@example.com",
        "status": "invited",
        "expires_at": {"$gt": now},
    }
    assert collection.calls[0][1]["$set"]["status"] == "accepting"
    assert collection.calls[1][0] == {
        "token_hash": "a" * 64,
        "email_normalized": "member@example.com",
        "status": "accepting",
        "accepted_by_user_id": "user-1",
        "acceptance_lease_expires_at": {"$lte": now},
        "expires_at": {"$gt": now},
    }


@pytest.mark.asyncio
async def test_invitation_claim_reclaims_an_expired_acceptance_lease_for_the_same_recipient():
    class ReclaimingCollection:
        def __init__(self):
            self.calls = 0

        async def find_one_and_update(self, _query, _update, **_kwargs):
            self.calls += 1
            return None if self.calls == 1 else {"status": "accepting", "acceptance_claim_id": "new-claim"}

    invitation = await OrganizationInvitationRepository(ReclaimingCollection()).claim_token(
        token_hash="c" * 64,
        email_normalized="member@example.com",
        accepted_by_user_id="user-1",
        claim_id="new-claim",
        now=datetime.now(timezone.utc),
    )

    assert invitation == {"status": "accepting", "acceptance_claim_id": "new-claim"}


@pytest.mark.asyncio
async def test_invitation_decline_requires_the_invited_email():
    collection = RecordingCollection()
    repository = OrganizationInvitationRepository(collection)
    now = datetime.now(timezone.utc)

    await repository.decline_token(
        token_hash="b" * 64,
        email_normalized="member@example.com",
        now=now,
    )

    assert collection.query["email_normalized"] == "member@example.com"


@pytest.mark.asyncio
async def test_invitation_pagination_uses_the_last_returned_invitation_as_cursor():
    invitations = [
        {"_id": ObjectId(), "status": "accepted", "expires_at": datetime.now(timezone.utc)}
        for _ in range(3)
    ]

    class Cursor:
        def sort(self, *_args):
            return self

        def limit(self, _value):
            return self

        async def to_list(self, *, length):
            assert length == 3
            return invitations

    class InvitationsCollection:
        def find(self, _query):
            return Cursor()

    page, next_cursor = await OrganizationInvitationRepository(
        InvitationsCollection()
    ).list_for_organization("org-1", limit=2, cursor=None)

    assert page == invitations[:2]
    assert next_cursor == str(invitations[1]["_id"])


@pytest.mark.asyncio
async def test_replacing_an_invitation_does_not_target_created_at_twice():
    collection = RecordingCollection()
    repository = OrganizationInvitationRepository(collection)
    now = datetime.now(timezone.utc)

    await repository.replace_open_invitation(
        {
            "organization_id": "org-1",
            "email_normalized": "member@example.com",
            "created_at": now,
            "updated_at": now,
        }
    )

    assert "created_at" not in collection.update["$set"]
    assert collection.update["$setOnInsert"]["created_at"] == now


def test_invitation_model_rejects_owner_role_even_outside_http_validation():
    with pytest.raises(ValidationError, match="owner role"):
        OrganizationInvitationDocument(
            organization_id="org-1",
            email="member@example.com",
            email_normalized="member@example.com",
            role="owner",
            token_hash="a" * 64,
            invited_by_user_id="user-1",
            expires_at=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize("status", ["invited"])
def test_membership_management_cannot_reinvite_members(status):
    with pytest.raises(ValidationError, match="reactivate.*suspend or remove"):
        UpdateOrganizationMembershipRequest(status=status)


def test_membership_management_allows_explicit_reactivation():
    assert UpdateOrganizationMembershipRequest(status="active").status == "active"


def test_invitation_decisions_require_a_verified_recipient():
    for route in (organization_routes.accept_invitation, organization_routes.decline_invitation):
        dependency = inspect.signature(route).parameters["current_user"].default
        assert dependency.dependency is get_verified_user


def test_shared_organization_creation_does_not_depend_on_active_organization_context():
    parameters = inspect.signature(organization_routes.create_organization).parameters

    assert "context" not in parameters
    assert parameters["current_user"].default.dependency is get_verified_user


@pytest.mark.asyncio
async def test_verified_user_can_create_an_organization_from_any_active_tenant(monkeypatch):
    captured = {}

    class Lifecycle:
        async def create_shared_organization(self, *, kind, name, owner_user_id):
            captured.update(kind=kind, name=name, owner_user_id=owner_user_id)
            return (
                {"_id": ObjectId(), "name": name, "kind": kind},
                {"role": "owner"},
            )

    monkeypatch.setattr(organization_routes, "OrganizationLifecycleService", lambda **_kwargs: Lifecycle())

    result = await organization_routes.create_organization.__wrapped__(
        request=SimpleNamespace(),
        payload=CreateOrganizationRequest(name="New workspace", kind="corporate"),
        current_user=SimpleNamespace(id="author-in-another-organization"),
    )

    assert captured["owner_user_id"] == "author-in-another-organization"
    assert result.role == "owner"


@pytest.mark.asyncio
async def test_unverified_recipient_is_rejected_before_invitation_decision():
    with pytest.raises(HTTPException) as exc_info:
        await get_verified_user(current_user=SimpleNamespace(is_verified=False))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_inviting_an_existing_active_member_is_rejected_before_creating_a_token():
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {
                "_id": ObjectId(organization_id),
                "status": "active",
                "kind": "corporate",
                "name": "Acme",
            }

    class MembershipsCollection:
        async def find_one(self, _query):
            return {"organization_id": organization_id, "user_id": "user-1", "status": "active"}

    class UsersCollection:
        async def find_one(self, _query, projection=None):
            return {"_id": "user-1"}

    class InvitationsCollection:
        async def find_one_and_update(self, *_args, **_kwargs):
            raise AssertionError("an active member must not receive a new invitation")

    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=MembershipsCollection(),
        invitations_collection=InvitationsCollection(),
        users_collection=UsersCollection(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.invite(
            organization_id=organization_id,
            inviter_user_id="owner-1",
            email="member@example.com",
            role="learner",
            expires_in_days=7,
            email_service=None,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_inviting_a_suspended_member_does_not_issue_a_reactivation_token():
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {"_id": ObjectId(organization_id), "status": "active", "kind": "corporate", "name": "Acme"}

    class MembershipsCollection:
        async def find_one(self, _query):
            return {"organization_id": organization_id, "user_id": "user-1", "status": "suspended"}

    class UsersCollection:
        async def find_one(self, _query, projection=None):
            return {"_id": "user-1"}

    class InvitationsCollection:
        async def find_one_and_update(self, *_args, **_kwargs):
            raise AssertionError("a suspended member must not receive a new invitation")

    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=MembershipsCollection(),
        invitations_collection=InvitationsCollection(),
        users_collection=UsersCollection(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.invite(
            organization_id=organization_id,
            inviter_user_id="owner-1",
            email="member@example.com",
            role="learner",
            expires_in_days=7,
            email_service=None,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_invitation_remains_usable_when_pending_membership_preparation_fails():
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {"_id": ObjectId(organization_id), "status": "active", "kind": "corporate", "name": "Acme"}

    class MembershipsCollection:
        async def find_one(self, _query):
            return None

        async def find_one_and_update(self, *_args, **_kwargs):
            raise RuntimeError("temporary membership write failure")

    class UsersCollection:
        async def find_one(self, _query, projection=None):
            return {"_id": "user-1"}

    class InvitationsCollection:
        async def find_one_and_update(self, _query, update, **_kwargs):
            return {"_id": ObjectId(), **update["$setOnInsert"], **update["$set"]}

    class EmailService:
        def __init__(self):
            self.sent = []

        async def send_email(self, **kwargs):
            self.sent.append(kwargs)

    email_service = EmailService()
    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=MembershipsCollection(),
        invitations_collection=InvitationsCollection(),
        users_collection=UsersCollection(),
    )

    invitation = await service.invite(
        organization_id=organization_id,
        inviter_user_id="owner-1",
        email="member@example.com",
        role="learner",
        expires_in_days=7,
        email_service=email_service,
    )

    assert invitation["organization_id"] == organization_id
    assert len(email_service.sent) == 1


@pytest.mark.asyncio
async def test_concurrent_member_activation_withdraws_the_new_invitation_before_delivery():
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {"_id": ObjectId(organization_id), "status": "active", "kind": "corporate", "name": "Acme"}

    class MembershipsCollection:
        async def find_one(self, _query):
            return None

        async def find_one_and_update(self, *_args, **_kwargs):
            return {"status": "active"}

    class UsersCollection:
        async def find_one(self, _query, projection=None):
            return {"_id": "user-1"}

    class InvitationsCollection:
        def __init__(self):
            self.revoked = False
            self.invitation_id = ObjectId()

        async def find_one_and_update(self, query, update, **_kwargs):
            if query.get("_id") == self.invitation_id:
                self.revoked = True
                return {"_id": self.invitation_id, "status": "revoked"}
            return {"_id": self.invitation_id, **update["$setOnInsert"], **update["$set"]}

    class EmailService:
        async def send_email(self, **_kwargs):
            raise AssertionError("stale invitation must not be delivered")

    invitations = InvitationsCollection()
    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=MembershipsCollection(),
        invitations_collection=invitations,
        users_collection=UsersCollection(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.invite(
            organization_id=organization_id,
            inviter_user_id="owner-1",
            email="member@example.com",
            role="learner",
            expires_in_days=7,
            email_service=EmailService(),
        )

    assert exc_info.value.status_code == 409
    assert invitations.revoked


@pytest.mark.asyncio
async def test_invitation_activation_refuses_to_revive_a_suspended_membership():
    class MembershipsCollection:
        async def find_one_and_update(self, *_args, **_kwargs):
            return None

        async def find_one(self, _query):
            return {"status": "suspended"}

    repository = OrganizationMembershipRepository(MembershipsCollection())

    with pytest.raises(InvitationMembershipStateError):
        await repository.activate_invitation(
            organization_id="org-1",
            user_id="user-1",
            role="learner",
            invited_by_user_id="owner-1",
        )


@pytest.mark.asyncio
async def test_acceptance_claims_activates_and_finalizes_the_invitation():
    invitation_id = ObjectId()
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {
                "_id": ObjectId(organization_id),
                "status": "active",
                "kind": "corporate",
                "name": "Acme",
            }

    class MembershipsCollection:
        async def find_one_and_update(self, _query, _update, **_kwargs):
            return {
                "organization_id": organization_id,
                "user_id": "user-1",
                "status": "active",
                "role": "learner",
            }

    class InvitationsCollection:
        def __init__(self):
            self.finalize_query = None

        async def find_one_and_update(self, query, _update, **_kwargs):
            if query.get("status") == "invited":
                return {
                    "_id": invitation_id,
                    "organization_id": organization_id,
                    "role": "learner",
                    "invited_by_user_id": "owner-1",
                }
            self.finalize_query = query
            return {
                "_id": invitation_id,
                "organization_id": organization_id,
                "status": "accepted",
                "accepted_by_user_id": "user-1",
            }

    invitations = InvitationsCollection()
    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=MembershipsCollection(),
        invitations_collection=invitations,
        users_collection=object(),
    )

    result = await service.accept(token="token", user_id="user-1", user_email="member@example.com")

    assert result["membership"]["status"] == "active"
    assert result["invitation"]["status"] == "accepted"
    assert invitations.finalize_query["status"] == "accepting"
    assert invitations.finalize_query["accepted_by_user_id"] == "user-1"


@pytest.mark.asyncio
async def test_second_acceptance_returns_conflict_while_the_first_claim_is_live():
    class InvitationsCollection:
        async def find_one_and_update(self, *_args, **_kwargs):
            return None

        async def find_one(self, _query):
            return {"status": "accepting", "accepted_by_user_id": "user-1"}

    service = OrganizationInvitationService(
        organizations_collection=object(),
        memberships_collection=object(),
        invitations_collection=InvitationsCollection(),
        users_collection=object(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.accept(token="token", user_id="user-1", user_email="member@example.com")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_acceptance_preserves_the_original_error_when_claim_restore_fails():
    invitation_id = ObjectId()
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {"_id": ObjectId(organization_id), "status": "active", "kind": "corporate", "name": "Acme"}

    class MembershipsCollection:
        async def find_one_and_update(self, _query, _update, **_kwargs):
            return {"organization_id": organization_id, "user_id": "user-1", "status": "active"}

    class InvitationsCollection:
        async def find_one_and_update(self, query, _update, **_kwargs):
            if query.get("status") == "invited":
                return {
                    "_id": invitation_id,
                    "organization_id": organization_id,
                    "role": "learner",
                    "invited_by_user_id": "owner-1",
                }
            raise RuntimeError("finalize failed")

        async def update_one(self, *_args, **_kwargs):
            raise RuntimeError("restore failed")

    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=MembershipsCollection(),
        invitations_collection=InvitationsCollection(),
        users_collection=object(),
    )

    with pytest.raises(RuntimeError, match="finalize failed"):
        await service.accept(token="token", user_id="user-1", user_email="member@example.com")


@pytest.mark.asyncio
async def test_personal_organizations_reject_member_invitations():
    organization_id = str(ObjectId())

    class OrganizationsCollection:
        async def find_one(self, _query):
            return {
                "_id": ObjectId(organization_id),
                "status": "active",
                "kind": "personal",
                "name": "Ada's workspace",
            }

    service = OrganizationInvitationService(
        organizations_collection=OrganizationsCollection(),
        memberships_collection=object(),
        invitations_collection=object(),
        users_collection=object(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.invite(
            organization_id=organization_id,
            inviter_user_id="owner-1",
            email="member@example.com",
            role="learner",
            expires_in_days=7,
            email_service=None,
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_shared_organization_creation_grants_the_creator_owner_membership():
    class OrganizationsCollection:
        async def insert_one(self, document):
            self.document = document
            return type("Result", (), {"inserted_id": ObjectId()})()

    class MembershipsCollection:
        async def find_one_and_update(self, _query, update, **_kwargs):
            return update["$setOnInsert"]

    organizations = OrganizationsCollection()
    service = OrganizationLifecycleService(
        organizations_collection=organizations,
        memberships_collection=MembershipsCollection(),
    )

    organization, membership = await service.create_shared_organization(
        kind="corporate",
        name="Acme Learning",
        owner_user_id="owner-1",
    )

    assert organization["kind"] == "corporate"
    assert organization["personal_owner_user_id"] is None
    assert membership["organization_id"] == str(organization["_id"])
    assert membership["user_id"] == "owner-1"
    assert membership["role"] == "owner"
