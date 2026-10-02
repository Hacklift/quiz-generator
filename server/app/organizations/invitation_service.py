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
    InvitationMembershipStateError,
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
            existing_membership = await self.memberships.get_membership(
                organization_id=organization_id,
                user_id=str(recipient["_id"]),
            )
            if existing_membership is not None and existing_membership.get("status") in {
                "active",
                "suspended",
            }:
                # Do not disclose whether an address maps to an active account
                # or an administrator-disabled membership.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An invitation cannot be created for this recipient",
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
            try:
                prepared_membership = await self.memberships.invite_known_user(
                    organization_id=organization_id,
                    user_id=str(recipient["_id"]),
                    role=role,
                    invited_by_user_id=inviter_user_id,
                )
                if prepared_membership.get("status") in {"active", "suspended"}:
                    # The membership changed after the pre-check. Withdraw the
                    # just-created token rather than sending authority that is
                    # no longer applicable. A failed withdrawal is logged;
                    # acceptance still cannot reactivate a suspension.
                    try:
                        await self.invitations.revoke(stored["_id"])
                    except Exception:
                        logger.exception(
                            "Unable to revoke stale organization invitation",
                            extra={"invitation_id": str(stored["_id"])},
                        )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An invitation cannot be created for this recipient",
                    )
            except HTTPException:
                raise
            except Exception:
                # The invitation is already durable and its acceptance path
                # can create the membership idempotently. Do not strand a
                # valid invitation or make a retry mandatory solely because
                # this optimisation failed.
                logger.exception(
                    "Unable to prepare organization invitation membership",
                    extra={
                        "organization_id": organization_id,
                        "invitation_id": str(stored["_id"]),
                        "recipient_user_id": str(recipient["_id"]),
                    },
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
            delivery_status = "sent"
        except Exception:
            # Keep the invitation valid so the manager can explicitly resend
            # it, but make the dispatch failure visible in the API and UI.
            logger.exception(
                "Organization invitation email dispatch failed",
                extra={"organization_id": organization_id, "invitation_id": str(stored["_id"])},
            )
            delivery_status = "failed"

        try:
            delivery_invitation = await self.invitations.mark_email_delivery(
                invitation_id=stored["_id"],
                token_hash=invitation["token_hash"],
                delivery_status=delivery_status,
            )
        except Exception:
            # Do not turn a successfully-created invitation into a failed
            # request solely because observability metadata could not be
            # written. The response still tells the manager the actual
            # provider-dispatch result for this attempt.
            logger.exception(
                "Unable to record organization invitation email delivery",
                extra={"organization_id": organization_id, "invitation_id": str(stored["_id"])},
            )
            delivery_invitation = None

        result = dict(delivery_invitation or stored)
        result["email_delivery_status"] = delivery_status
        return result

    async def accept(self, *, token: str, user_id: str, user_email: str) -> dict[str, Any]:
        now = utcnow()
        token_hash = _token_hash(token)
        email_normalized = normalize_email(user_email)
        claim_id = secrets.token_urlsafe(24)
        invitation = await self.invitations.claim_token(
            token_hash=token_hash,
            email_normalized=email_normalized,
            accepted_by_user_id=user_id,
            claim_id=claim_id,
            now=now,
        )
        if invitation is None:
            existing = await self.invitations.get_for_token_and_recipient(
                token_hash=token_hash,
                email_normalized=email_normalized,
            )
            if (
                existing is not None
                and existing.get("status") == "accepted"
                and existing.get("accepted_by_user_id") == user_id
            ):
                membership = await self.memberships.get_active_membership(
                    organization_id=existing["organization_id"],
                    user_id=user_id,
                )
                if membership is not None:
                    return {"invitation": existing, "membership": membership}
            if (
                existing is not None
                and existing.get("status") == "accepting"
                and existing.get("accepted_by_user_id") == user_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Invitation acceptance is in progress; retry shortly",
                )
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
            finalized = await self.invitations.finalize_claim(
                invitation_id=invitation["_id"],
                claim_id=claim_id,
                accepted_by_user_id=user_id,
                now=utcnow(),
            )
            if finalized is None:
                # The membership write is idempotent. Do not report success
                # until the invitation's audit state records the same outcome.
                raise RuntimeError("Invitation acceptance claim was lost")
        except InvitationMembershipStateError as exc:
            await self._restore_claim_safely(invitation, user_id, claim_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This membership must be reactivated by an organization administrator",
            ) from exc
        except Exception:
            await self._restore_claim_safely(invitation, user_id, claim_id)
            raise
        return {"invitation": finalized, "membership": membership}

    async def _restore_claim_safely(
        self,
        invitation: dict[str, Any],
        user_id: str,
        claim_id: str,
    ) -> None:
        """Preserve the triggering error if recovery of a claimed token fails.

        A failed restore leaves an expiring `accepting` lease that the intended
        recipient can reclaim. It must never turn a transient database issue
        into a permanently burned invitation or mask its root cause.
        """
        try:
            await self.invitations.restore_consumed_invitation(
                invitation_id=invitation["_id"],
                accepted_by_user_id=user_id,
                claim_id=claim_id,
            )
        except Exception:
            logger.exception(
                "Unable to restore organization invitation acceptance claim",
                extra={"invitation_id": str(invitation["_id"])},
            )

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

    async def get_for_revoke(self, *, invitation_id: str, organization_id: str) -> dict[str, Any]:
        try:
            object_id = ObjectId(invitation_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Invitation not found") from exc
        invitation = await self.invitations.get_for_organization(object_id, organization_id)
        if invitation is None:
            raise HTTPException(status_code=404, detail="Invitation not found")
        return invitation

    async def revoke(
        self,
        *,
        invitation_id: str,
        organization_id: str,
        expected_role: str,
    ) -> dict[str, Any]:
        try:
            object_id = ObjectId(invitation_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Invitation not found") from exc
        updated = await self.invitations.revoke(object_id, expected_role=expected_role)
        if updated is None:
            # This also covers a role change between the authorization read
            # and conditional revoke. Never revoke a differently privileged
            # invitation based on stale authorization.
            raise HTTPException(status_code=409, detail="Invitation changed; refresh and retry")
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
        users_collection: AsyncIOMotorCollection | None = None,
    ):
        self.organizations = OrganizationRepository(organizations_collection)
        self.memberships = OrganizationMembershipRepository(memberships_collection)
        self.users_collection = users_collection

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
            # The organization remains inaccessible in `provisioning` state.
            # A deployment reconciliation can finish it once Mongo recovers;
            # never expose or destructively delete a partially-created tenant.
            logger.exception(
                "Shared organization owner membership provisioning failed",
                extra={"organization_id": str(organization["_id"])},
            )
            raise
        active_organization = await self.organizations.activate_provisioned_shared_organization(
            organization_id=str(organization["_id"]),
            owner_user_id=owner_user_id,
        )
        if active_organization is None:
            raise RuntimeError("Shared organization provisioning could not be activated")
        return active_organization, membership

    async def reconcile_provisioning_shared_organizations(self) -> tuple[int, list[str]]:
        """Finish only safely attributable interrupted shared-tenant creates.

        This is deliberately narrower than a generic owner repair: it never
        changes active, suspended, or archived organizations and never invents
        an owner for an organization without a recorded creator.
        """
        reconciled = 0
        unresolved: list[str] = []
        if self.users_collection is None:
            logger.error("Shared organization reconciliation requires a users collection")
            return reconciled, ["users_collection_unavailable"]
        for organization in await self.organizations.list_provisioning_shared_organizations():
            organization_id = str(organization["_id"])
            owner_user_id = organization.get("created_by_user_id")
            if not isinstance(owner_user_id, str) or not owner_user_id:
                unresolved.append(organization_id)
                continue
            if not ObjectId.is_valid(owner_user_id):
                unresolved.append(organization_id)
                continue
            owner = await self.users_collection.find_one(
                {"_id": ObjectId(owner_user_id), "status": {"$ne": "deleted"}},
                projection={"_id": 1},
            )
            if owner is None:
                unresolved.append(organization_id)
                continue
            membership = await self.memberships.create_owner_membership(
                organization_id=organization_id,
                user_id=owner_user_id,
            )
            if membership.get("role") != "owner" or membership.get("status") != "active":
                unresolved.append(organization_id)
                continue
            active_organization = await self.organizations.activate_provisioned_shared_organization(
                organization_id=organization_id,
                owner_user_id=owner_user_id,
            )
            if active_organization is None:
                unresolved.append(organization_id)
                continue
            reconciled += 1
        return reconciled, unresolved
