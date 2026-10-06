from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import HTTPException, status

from server.app.organizations.models import (
    MembershipRole,
    OrganizationContext,
    OrganizationPrincipal,
)


class OrganizationAction(StrEnum):
    ORGANIZATION_MANAGE = "organization.manage"
    MEMBERSHIP_MANAGE = "membership.manage"
    MEMBERSHIP_ADMIN_MANAGE = "membership.admin.manage"
    BILLING_MANAGE = "billing.manage"
    CONTENT_CREATE = "content.create"
    CONTENT_READ = "content.read"
    CONTENT_UPDATE = "content.update"
    CONTENT_DELETE = "content.delete"
    CONTENT_SHARE = "content.share"
    CONTENT_EXPORT = "content.export"
    DELIVERY_READ = "delivery.read"
    DELIVERY_RUN = "delivery.run"
    REPORT_READ = "report.read"
    AUDIT_READ = "audit.read"
    ATTEMPT_COMPLETE = "attempt.complete"


_ROLE_ACTIONS: dict[MembershipRole, frozenset[OrganizationAction]] = {
    "owner": frozenset(OrganizationAction),
    "admin": frozenset(
        {
            OrganizationAction.ORGANIZATION_MANAGE,
            OrganizationAction.MEMBERSHIP_MANAGE,
            OrganizationAction.CONTENT_CREATE,
            OrganizationAction.CONTENT_READ,
            OrganizationAction.CONTENT_UPDATE,
            OrganizationAction.CONTENT_DELETE,
            OrganizationAction.CONTENT_SHARE,
            OrganizationAction.CONTENT_EXPORT,
            OrganizationAction.DELIVERY_RUN,
            OrganizationAction.DELIVERY_READ,
            OrganizationAction.REPORT_READ,
            OrganizationAction.AUDIT_READ,
        }
    ),
    "author": frozenset(
        {
            OrganizationAction.CONTENT_CREATE,
            OrganizationAction.CONTENT_READ,
            OrganizationAction.CONTENT_UPDATE,
            OrganizationAction.CONTENT_DELETE,
            OrganizationAction.CONTENT_SHARE,
            OrganizationAction.CONTENT_EXPORT,
        }
    ),
    "facilitator": frozenset(
        {
            OrganizationAction.CONTENT_READ,
            OrganizationAction.DELIVERY_RUN,
            OrganizationAction.REPORT_READ,
        }
    ),
    "learner": frozenset(
        {
            OrganizationAction.CONTENT_CREATE,
            OrganizationAction.CONTENT_READ,
            OrganizationAction.ATTEMPT_COMPLETE,
        }
    ),
    "guardian": frozenset(),
    "auditor": frozenset(
        {
            OrganizationAction.REPORT_READ,
            OrganizationAction.AUDIT_READ,
        }
    ),
}

# These actions authorize creating or administering state within the already
# proven organization context. Every action against an existing resource must
# receive that resource so tenant and relationship checks cannot be skipped by
# a future route implementation.
_RESOURCELESS_ACTIONS = frozenset(
    {
        OrganizationAction.ORGANIZATION_MANAGE,
        OrganizationAction.MEMBERSHIP_MANAGE,
        OrganizationAction.MEMBERSHIP_ADMIN_MANAGE,
        OrganizationAction.BILLING_MANAGE,
        OrganizationAction.CONTENT_CREATE,
        OrganizationAction.DELIVERY_READ,
    }
)


class OrganizationPolicy:
    """Single authorization decision point for organization-scoped resources.

    Role permissions are only the first gate. Ownership, assignments, explicit
    visibility, and guardian relationships are resource facts evaluated here,
    rather than route-local role checks.
    """

    @staticmethod
    def _resource_relates_to_principal(
        resource: dict[str, Any] | None,
        principal: OrganizationPrincipal,
        *fields: str,
    ) -> bool:
        """Match persisted resource relationships without widening tenant access.

        `created_by_user_id` is the canonical authorship field. `owner_user_id`
        remains a compatibility fallback for legacy canonical quizzes that were
        scoped before authorship was populated. Assignment-backed resources use
        their existing recipient/user fields; a missing relationship never
        grants access.
        """
        return bool(
            resource
            and any(
                resource.get(field) is not None
                and str(resource[field]) == principal.user_id
                for field in fields
            )
        )

    def can(
        self,
        principal: OrganizationPrincipal,
        action: OrganizationAction,
        resource: dict[str, Any] | None,
        context: OrganizationContext,
    ) -> bool:
        if principal.user_id != context.principal.user_id:
            return False
        if resource is None and action not in _RESOURCELESS_ACTIONS:
            return False
        if resource is not None and str(resource.get("organization_id")) != context.organization_id:
            return False

        role = context.membership_role
        if action not in _ROLE_ACTIONS[role]:
            return False

        if role == "author" and action in {
            OrganizationAction.CONTENT_UPDATE,
            OrganizationAction.CONTENT_DELETE,
            OrganizationAction.CONTENT_SHARE,
            OrganizationAction.CONTENT_EXPORT,
        }:
            return self._resource_relates_to_principal(
                resource,
                principal,
                "created_by_user_id",
                "owner_user_id",
            )

        if role == "facilitator" and action in {
            OrganizationAction.DELIVERY_RUN,
            OrganizationAction.REPORT_READ,
        }:
            # Explicit facilitator delegation is future-facing. Existing
            # delivery records only persist a creator/owner relationship, so
            # a facilitator may operate delivery they created, never every
            # delivery in the organization merely by role membership.
            return self._resource_relates_to_principal(
                resource,
                principal,
                "facilitator_user_id",
                "created_by_user_id",
                "owner_user_id",
            )

        if role == "learner" and action == OrganizationAction.CONTENT_READ:
            # Learners may read self-authored practice content as well as
            # resources explicitly assigned to them. Public/unlisted content
            # is handled by its explicit capability path before this policy.
            return self._resource_relates_to_principal(
                resource,
                principal,
                "assigned_user_id",
                "recipient_user_id",
                "created_by_user_id",
                "owner_user_id",
                "user_id",
            )

        if role == "learner" and action == OrganizationAction.ATTEMPT_COMPLETE:
            return self._resource_relates_to_principal(
                resource,
                principal,
                "assigned_user_id",
                "recipient_user_id",
                "user_id",
            )

        return True


def require_organization_permission(
    *,
    context: OrganizationContext,
    action: OrganizationAction,
    resource: dict[str, Any] | None,
) -> None:
    """Enforce a policy decision without revealing cross-tenant resources.

    A resource from another organization is indistinguishable from a missing
    resource. A resource in the active organization that the member cannot
    operate on produces a normal authorization error.
    """
    if resource is not None and str(resource.get("organization_id")) != context.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if not OrganizationPolicy().can(context.principal, action, resource, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization permission denied")
