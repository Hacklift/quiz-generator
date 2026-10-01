from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.core.config import settings
from server.app.email_platform.service import EmailService
from server.app.organizations.models import OrganizationInvitationDocument, utcnow
from server.app.organizations.repository import (
    OrganizationInvitationRepository,
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from server.app.users.identity import normalize_email


logger = logging.getLogger(__name__)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class OrganizationInvitationService:
    """Coordinates invitation delivery with membership activation.

    An invitation is not itself authority. The recipient's authenticated email
    must match the invitation before an active membership is written.
    """

    def __init__(
        self,
        *,
        organizations_collection: AsyncIOMotorCollection,
        memberships_collection: AsyncIOMotorCollection,
        invitations_collection: AsyncIOMotorCollection,
        users_collection: AsyncIOMotorCollection,
    ):
        self.organizations = OrganizationRepository(organizations_collection)
        self.memberships = OrganizationMembershipRepository(memberships_collection)
        self.invitations = OrganizationInvitationRepository(invitations_collection)
        self.users_collection = users_collection

    async def invite(
        self,
        *,
        organization_id: str,
        inviter_user_id: str,
        email: str,
        role: str,
        expires_in_days: int,
        email_service: EmailService,
    ) -> dict[str, Any]:
        organization = await self.organizations.get_active(organization_id)
        if organization is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        if organization["kind"] == "personal" or organization.get("system_key"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitations are available only for shared organizations",
            )

        email_normalized = normalize_email(email)
        recipient = await self.users_collection.find_one(
            {"email_normalized": email_normalized, "status": {"$ne": "deleted"}},
            projection={"_id": 1},
        )
        if recipient is not None:
            existing_membership = await self.memberships.get_active_membership(
                organization_id=organization_id,
                user_id=str(recipient["_id"]),
            )
            if existing_membership is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This person already has an active organization membership",
                )
        now = utcnow()
        token = secrets.token_urlsafe(32)
        invitation = OrganizationInvitationDocument(
            organization_id=organization_id,
            email=email,
            email_normalized=email_normalized,
            role=role,
            token_hash=_token_hash(token),
            invited_by_user_id=inviter_user_id,
            expires_at=now + timedelta(days=expires_in_days),
            created_at=now,
            updated_at=now,
        ).model_dump(by_alias=True)
        invitation.pop("_id", None)
        stored = await self.invitations.replace_open_invitation(invitation)

        # Record the pending lifecycle state immediately when the recipient
        # already has an account. Unknown-email invitations become a
        # membership only after that address authenticates and accepts.
        if recipient is not None:
            await self.memberships.invite_known_user(
                organization_id=organization_id,
                user_id=str(recipient["_id"]),
                role=role,
                invited_by_user_id=inviter_user_id,
            )

        invitation_url = (
            f"{settings.FRONTEND_BASE_URL}/organizations/invitations/accept?token={token}"
        )
        try:
            await email_service.send_email(
                to=email,
                template_id="organization_invitation",
                template_vars={
                    "subject": f"You're invited to {organization['name']} on Quizwerk",
                    "body": (
                        f"You've been invited to join {organization['name']} as a {role}.\n\n"
                        f"Accept or decline this invitation: {invitation_url}\n\n"
                        f"This invitation expires on {stored['expires_at'].isoformat()}."
                    ),
                },
                purpose="organization_invitation",
            )
        except Exception:
            # Delivery is retriable separately from the durable invitation;
            # never discard authority state after generating a valid link.
            logger.exception(
                "Organization invitation email dispatch failed",
                extra={"organization_id": organization_id, "invitation_id": str(stored["_id"])},
            )

        return stored

    async def accept(self, *, token: str, user_id: str, user_email: str) -> dict[str, Any]:
        now = utcnow()
        invitation = await self.invitations.consume_token(
            token_hash=_token_hash(token),
            email_normalized=normalize_email(user_email),
            accepted_by_user_id=user_id,
            now=now,
        )
        if invitation is None:
            # Do not reveal whether a valid invitation exists for a different
            # address. The e-mail match is part of the atomic consume query.
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is invalid or expired")
        try:
            organization = await self.organizations.get_active(invitation["organization_id"])
            if organization is None or organization["kind"] == "personal" or organization.get("system_key"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This organization is no longer available for invitations",
                )
            membership = await self.memberships.activate_invitation(
                organization_id=invitation["organization_id"],
                user_id=user_id,
                role=invitation["role"],
                invited_by_user_id=invitation["invited_by_user_id"],
            )
        except Exception:
            await self.invitations.restore_consumed_invitation(
                invitation_id=invitation["_id"],
                accepted_by_user_id=user_id,
            )
            raise
        return {"invitation": invitation, "membership": membership}

    async def decline(self, *, token: str, user_email: str) -> dict[str, Any]:
        invitation = await self.invitations.decline_token(
            token_hash=_token_hash(token),
            email_normalized=normalize_email(user_email),
            now=utcnow(),
        )
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation is invalid or expired")
        await self._remove_pending_membership(invitation)
        return invitation

    async def revoke(self, *, invitation_id: str, organization_id: str) -> dict[str, Any]:
        try:
            object_id = ObjectId(invitation_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Invitation not found") from exc
        invitation = await self.invitations.get_for_organization(object_id, organization_id)
        if invitation is None:
            raise HTTPException(status_code=404, detail="Invitation not found")
        updated = await self.invitations.revoke(object_id)
        if updated is None:
            raise HTTPException(status_code=409, detail="Invitation can no longer be revoked")
        await self._remove_pending_membership(updated)
        return updated

    async def _remove_pending_membership(self, invitation: dict[str, Any]) -> None:
        recipient = await self.users_collection.find_one(
            {"email_normalized": invitation["email_normalized"]},
            projection={"_id": 1},
        )
        if recipient is not None:
            await self.memberships.remove_pending_invitation(
                organization_id=invitation["organization_id"],
                user_id=str(recipient["_id"]),
            )


class OrganizationLifecycleService:
    """Creates shared workspaces and their initial owner membership."""

    def __init__(
        self,
        *,
        organizations_collection: AsyncIOMotorCollection,
        memberships_collection: AsyncIOMotorCollection,
    ):
        self.organizations = OrganizationRepository(organizations_collection)
        self.memberships = OrganizationMembershipRepository(memberships_collection)

    async def create_shared_organization(
        self,
        *,
        kind: str,
        name: str,
        owner_user_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if kind == "personal":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Personal organizations are created automatically for each user",
            )
        organization = await self.organizations.create_shared_organization(
            kind=kind,
            name=name,
            created_by_user_id=owner_user_id,
        )
        try:
            membership = await self.memberships.create_owner_membership(
                organization_id=str(organization["_id"]),
                user_id=owner_user_id,
            )
        except Exception:
            # This is a newly-created tenant with no valid owner; remove it
            # rather than leaving an inaccessible workspace behind.
            try:
                await self.organizations.collection.delete_one({"_id": organization["_id"]})
            except Exception:
                logger.exception(
                    "Unable to compensate an organization without an owner membership",
                    extra={"organization_id": str(organization["_id"])},
                )
            raise
        return organization, membership
