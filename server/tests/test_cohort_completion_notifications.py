from bson import ObjectId
import pytest

from server.app.assignments.authorization import may_receive_assignment_completion


@pytest.mark.parametrize("role,can_report,expected", [
    ("owner", False, True), ("admin", False, True),
    ("facilitator", False, False), ("facilitator", True, True),
    ("learner", False, False), ("guardian", True, False),
])
def test_completion_notifications_follow_independent_reporting_delegation(role, can_report, expected):
    organization_id, owner_id, cohort_id = map(str, [ObjectId(), ObjectId(), ObjectId()])
    run = {
        "organization_id": organization_id, "owner_user_id": owner_id,
        "created_by_user_id": owner_id, "cohort_id": cohort_id, "delivery_kind": "quiz",
    }
    membership = {"organization_id": organization_id, "user_id": owner_id, "role": role, "status": "active"}
    delegation = {
        "organization_id": organization_id, "cohort_id": cohort_id, "user_id": owner_id,
        "role": "guardian" if role == "guardian" else "facilitator",
        "status": "active", "can_assign": True, "can_report": can_report,
    }
    organization = {"_id": ObjectId(organization_id), "kind": "school", "status": "active"}
    assert may_receive_assignment_completion(run, membership, delegation, organization=organization) is expected
    membership["status"] = "suspended"
    assert not may_receive_assignment_completion(run, membership, delegation, organization=organization)


def test_completion_notifications_do_not_cross_tenants_or_disabled_organizations():
    organization_id, owner_id = map(str, [ObjectId(), ObjectId()])
    run = {"organization_id": organization_id, "owner_user_id": owner_id, "delivery_kind": "quiz"}
    member = {"organization_id": organization_id, "user_id": owner_id, "role": "owner", "status": "active"}
    organization = {"_id": ObjectId(), "kind": "corporate", "status": "active"}
    assert not may_receive_assignment_completion(run, member, organization=organization)
    organization.update(_id=ObjectId(organization_id), status="suspended")
    assert not may_receive_assignment_completion(run, member, organization=organization)


def test_legacy_training_notification_behavior_is_preserved():
    assert may_receive_assignment_completion({"kind": "business"}, None)
