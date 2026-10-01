from __future__ import annotations

import os
from datetime import datetime, timezone

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
from server.app.organizations.repository import OrganizationInvitationRepository
from server.app.organizations.schemas import UpdateOrganizationMembershipRequest


class RecordingCollection:
    def __init__(self):
        self.query = None
        self.update = None

    async def find_one_and_update(self, query, update, **_kwargs):
        self.query = query
        self.update = update
        return None


@pytest.mark.asyncio
async def test_invitation_consumption_binds_the_one_time_token_to_the_invited_email():
    collection = RecordingCollection()
    repository = OrganizationInvitationRepository(collection)
    now = datetime.now(timezone.utc)

    await repository.consume_token(
        token_hash="a" * 64,
        email_normalized="member@example.com",
        accepted_by_user_id="user-1",
        now=now,
    )

    assert collection.query == {
        "token_hash": "a" * 64,
        "email_normalized": "member@example.com",
        "status": "invited",
        "expires_at": {"$gt": now},
    }


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


@pytest.mark.parametrize("status", ["active", "invited"])
def test_membership_management_cannot_activate_or_reinvite_members(status):
    with pytest.raises(ValidationError, match="only suspend or remove"):
        UpdateOrganizationMembershipRequest(status=status)


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
