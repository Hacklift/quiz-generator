from __future__ import annotations

import pytest
from bson import ObjectId

from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.policy import OrganizationAction, OrganizationPolicy


ALL_ACTIONS = tuple(OrganizationAction)
EXPECTED_ACTIONS = {
    "owner": set(ALL_ACTIONS),
    "admin": {
        OrganizationAction.ORGANIZATION_MANAGE,
        OrganizationAction.MEMBERSHIP_MANAGE,
        OrganizationAction.CONTENT_CREATE,
        OrganizationAction.CONTENT_READ,
        OrganizationAction.CONTENT_UPDATE,
        OrganizationAction.CONTENT_DELETE,
        OrganizationAction.CONTENT_SHARE,
        OrganizationAction.CONTENT_EXPORT,
        OrganizationAction.DELIVERY_READ,
        OrganizationAction.DELIVERY_RUN,
        OrganizationAction.REPORT_READ,
        OrganizationAction.AUDIT_READ,
    },
    "author": {
        OrganizationAction.CONTENT_CREATE,
        OrganizationAction.CONTENT_READ,
        OrganizationAction.CONTENT_UPDATE,
        OrganizationAction.CONTENT_DELETE,
        OrganizationAction.CONTENT_SHARE,
        OrganizationAction.CONTENT_EXPORT,
    },
    "facilitator": {
        OrganizationAction.CONTENT_READ,
        OrganizationAction.DELIVERY_RUN,
        OrganizationAction.REPORT_READ,
    },
    "learner": {
        OrganizationAction.CONTENT_CREATE,
        OrganizationAction.CONTENT_READ,
        OrganizationAction.ATTEMPT_COMPLETE,
    },
    "guardian": set(),
    "auditor": {OrganizationAction.REPORT_READ, OrganizationAction.AUDIT_READ},
}


def _context(role: str, user_id: str = "user-1") -> OrganizationContext:
    principal = OrganizationPrincipal(user_id=user_id, session_id="session-1")
    return OrganizationContext(
        organization_id="507f1f77bcf86cd799439011",
        organization_kind="corporate",
        membership_role=role,
        principal=principal,
        membership={"role": role, "status": "active"},
    )


@pytest.mark.parametrize("role", tuple(EXPECTED_ACTIONS))
@pytest.mark.parametrize("action", ALL_ACTIONS)
def test_role_action_matrix(role: str, action: OrganizationAction):
    context = _context(role)
    resource = {
        "organization_id": context.organization_id,
        "created_by_user_id": context.principal.user_id,
        "assigned_user_id": context.principal.user_id,
        "facilitator_user_id": context.principal.user_id,
    }

    assert OrganizationPolicy().can(context.principal, action, resource, context) is (
        action in EXPECTED_ACTIONS[role]
    )


def test_author_cannot_edit_another_members_content():
    context = _context("author")
    resource = {
        "organization_id": context.organization_id,
        "created_by_user_id": "another-user",
    }

    assert not OrganizationPolicy().can(
        context.principal,
        OrganizationAction.CONTENT_UPDATE,
        resource,
        context,
    )


def test_learner_cannot_complete_another_members_assignment():
    context = _context("learner")
    resource = {
        "organization_id": context.organization_id,
        "assigned_user_id": "another-user",
    }

    assert not OrganizationPolicy().can(
        context.principal,
        OrganizationAction.ATTEMPT_COMPLETE,
        resource,
        context,
    )


@pytest.mark.parametrize(
    ("role", "action", "resource"),
    [
        ("facilitator", OrganizationAction.DELIVERY_RUN, None),
        ("facilitator", OrganizationAction.REPORT_READ, {"organization_id": "507f1f77bcf86cd799439011"}),
        ("learner", OrganizationAction.ATTEMPT_COMPLETE, None),
        ("learner", OrganizationAction.CONTENT_READ, {"organization_id": "507f1f77bcf86cd799439011"}),
    ],
)
def test_assignment_bound_roles_fail_closed_without_an_assigned_resource(
    role: str,
    action: OrganizationAction,
    resource: dict | None,
):
    context = _context(role)

    assert not OrganizationPolicy().can(context.principal, action, resource, context)


def test_policy_rejects_cross_organization_resource_before_role_evaluation():
    context = _context("owner")

    assert not OrganizationPolicy().can(
        context.principal,
        OrganizationAction.CONTENT_READ,
        {"organization_id": "507f1f77bcf86cd799439012"},
        context,
    )


def test_policy_accepts_object_id_organization_references():
    organization_id = ObjectId()
    context = _context("owner")
    context.organization_id = str(organization_id)

    assert OrganizationPolicy().can(
        context.principal,
        OrganizationAction.CONTENT_READ,
        {"organization_id": organization_id},
        context,
    )


@pytest.mark.parametrize(
    ("role", "action", "relationship_field"),
    [
        ("author", OrganizationAction.CONTENT_UPDATE, "created_by_user_id"),
        ("facilitator", OrganizationAction.DELIVERY_RUN, "facilitator_user_id"),
        ("learner", OrganizationAction.ATTEMPT_COMPLETE, "assigned_user_id"),
    ],
)
def test_policy_accepts_object_id_relationship_references(
    role: str,
    action: OrganizationAction,
    relationship_field: str,
):
    user_id = ObjectId()
    context = _context(role, user_id=str(user_id))

    assert OrganizationPolicy().can(
        context.principal,
        action,
        {
            "organization_id": context.organization_id,
            relationship_field: user_id,
        },
        context,
    )


def test_policy_rejects_principal_that_does_not_match_context():
    context = _context("owner")
    other_principal = OrganizationPrincipal(user_id="user-2", session_id="session-2")

    assert not OrganizationPolicy().can(
        other_principal,
        OrganizationAction.CONTENT_READ,
        {"organization_id": context.organization_id},
        context,
    )


def test_only_an_owner_can_manage_administrator_memberships():
    admin_context = _context("admin")
    owner_context = _context("owner")

    assert not OrganizationPolicy().can(
        admin_context.principal,
        OrganizationAction.MEMBERSHIP_ADMIN_MANAGE,
        None,
        admin_context,
    )
    assert OrganizationPolicy().can(
        owner_context.principal,
        OrganizationAction.MEMBERSHIP_ADMIN_MANAGE,
        None,
        owner_context,
    )


@pytest.mark.parametrize(
    "action",
    (
        OrganizationAction.CONTENT_READ,
        OrganizationAction.CONTENT_UPDATE,
        OrganizationAction.CONTENT_DELETE,
        OrganizationAction.CONTENT_SHARE,
        OrganizationAction.CONTENT_EXPORT,
        OrganizationAction.DELIVERY_RUN,
        OrganizationAction.REPORT_READ,
        OrganizationAction.AUDIT_READ,
        OrganizationAction.ATTEMPT_COMPLETE,
    ),
)
def test_resource_sensitive_actions_fail_closed_without_a_loaded_resource(action):
    context = _context("owner")

    assert not OrganizationPolicy().can(context.principal, action, None, context)
