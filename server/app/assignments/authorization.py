"""Shared reporting authorization for API and worker notification delivery."""

from pydantic import ValidationError

from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.policy import OrganizationAction, OrganizationPolicy


def may_receive_assignment_completion(run, organization_membership, cohort_membership=None, *, organization=None):
    """An assignment creator is not necessarily authorized to see results."""
    if run.get("delivery_kind") != "quiz":
        return True
    owner = run.get("owner_user_id")
    organization_id = run.get("organization_id")
    member = organization_membership or {}
    organization = organization or {}
    if not (
        owner and organization_id and member.get("status") == "active"
        and member.get("organization_id") == organization_id
        and member.get("user_id") == owner
        and organization.get("status") == "active"
        and str(organization.get("_id")) == organization_id
    ):
        return False
    try:
        principal = OrganizationPrincipal(user_id=owner, session_id="completion-notification")
        context = OrganizationContext(
            organization_id=organization_id,
            organization_kind=organization["kind"],
            membership_role=member["role"],
            membership=member,
            principal=principal,
        )
    except (KeyError, ValidationError):
        return False
    return OrganizationPolicy().can(
        principal,
        OrganizationAction.COHORT_REPORT,
        {**run, "cohort_membership": cohort_membership},
        context,
    )
