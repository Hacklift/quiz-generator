from __future__ import annotations

from enum import StrEnum
from typing import Any

from server.app.organizations.models import (
    MembershipRole,
    OrganizationContext,
    OrganizationPrincipal,
)


class OrganizationAction(StrEnum):
    ORGANIZATION_MANAGE = "organization.manage"
    MEMBERSHIP_MANAGE = "membership.manage"
    BILLING_MANAGE = "billing.manage"
    CONTENT_CREATE = "content.create"
    CONTENT_READ = "content.read"
    CONTENT_UPDATE = "content.update"
    CONTENT_DELETE = "content.delete"
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
            OrganizationAction.DELIVERY_RUN,
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
        OrganizationAction.BILLING_MANAGE,
        OrganizationAction.CONTENT_CREATE,
    }
)


class OrganizationPolicy:
    """Single authorization decision point for organization-scoped resources.

    Role permissions are only the first gate. Ownership, assignments, explicit
    visibility, and guardian relationships are resource facts evaluated here,
    rather than route-local role checks.
    """

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
        }:
            return bool(
                resource
                and str(resource.get("created_by_user_id")) == principal.user_id
            )

        if role == "facilitator" and action in {
            OrganizationAction.DELIVERY_RUN,
            OrganizationAction.REPORT_READ,
        }:
            return bool(
                resource
                and str(resource.get("facilitator_user_id")) == principal.user_id
            )

        if role == "learner" and action in {
            OrganizationAction.CONTENT_READ,
            OrganizationAction.ATTEMPT_COMPLETE,
        }:
            return bool(
                resource
                and str(resource.get("assigned_user_id")) == principal.user_id
            )

        return True
