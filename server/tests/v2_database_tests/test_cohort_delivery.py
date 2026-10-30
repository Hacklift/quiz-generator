"""Real Mongo coverage of the cohort-to-delivery-to-report workflow."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from slowapi.errors import RateLimitExceeded
import pytest
import pytest_asyncio

from server.app.assignments.dependencies import CohortDeliveryAdapter, get_assignment_service
from server.app.assignments.models import CreateAssignmentRequest
from server.app.assignments.repository import AssignmentRepository
from server.app.assignments.revisions import QuizRevisionRepository
from server.app.assignments.routes import router as assignments_router, progress_router
from server.app.assignments.service import AssignmentService
from server.app.assignments.validators import ensure_assignment_collections
from server.app.cohorts.dependencies import get_cohort_service
from server.app.cohorts.repository import CohortRepository
from server.app.cohorts.routes import router as cohorts_router
from server.app.cohorts.schemas import CreateCohortRequest, SetCohortMemberRequest
from server.app.cohorts.service import CohortService
from server.app.cohorts.validators import ensure_cohort_collections
from server.app.core.dependencies import get_verified_user
from server.app.core.dependencies import get_current_user
from server.app.db.core.connection import (
    get_organization_memberships_collection, get_organizations_collection,
    get_user_sessions_collection,
)
from server.app.core.rate_limiter import limiter, rate_limit_handler
from server.app.db.core.connection import ensure_training_run_indexes
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.quiz.repositories.live_session_repository import LiveQuizSessionRepository
from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.services.training_run_service import TrainingRunService


@pytest_asyncio.fixture
async def delivery(test_db, monkeypatch):
    db = test_db
    await ensure_cohort_collections(db)
    await ensure_assignment_collections(db)
    await ensure_training_run_indexes(db.training_runs, db.training_assignments,
                                     db.training_audit_events, db.training_email_deliveries)
    org = str(ObjectId())
    ids = {name: str(ObjectId()) for name in ("owner", "learner", "facilitator", "other")}
    await db.organizations.insert_one({"_id": ObjectId(org), "kind": "school", "status": "active"})
    contexts = {}
    users = {}
    now = datetime.now(timezone.utc)
    for name, user_id in ids.items():
        role = "owner" if name == "owner" else "facilitator" if name == "facilitator" else "learner"
        await db.users.insert_one({"_id": ObjectId(user_id), "username": name,
                                  "email": f"{name}@example.com", "is_verified": True, "status": "active"})
        member = {"organization_id": org, "user_id": user_id, "role": role, "status": "active"}
        await db.organization_memberships.insert_one(dict(member))
        session_id = f"cohort-test-{name}"
        await db.user_sessions.insert_one({"session_id": session_id, "user_id": user_id,
                                          "active_organization_id": org, "revoked_at": None,
                                          "expires_at": now + timedelta(days=1)})
        contexts[name] = OrganizationContext(
            organization_id=org, organization_kind="school", membership_role=role, membership=member,
            principal=OrganizationPrincipal(user_id=user_id, session_id=session_id),
        )
        users[name] = SimpleNamespace(id=user_id, email=f"{name}@example.com", username=name,
                                      full_name=name, session_id=session_id)
    quiz = QuizDocumentV2(
        organization_id=org, owner_user_id=ids["owner"], created_by_user_id=ids["owner"],
        title="Frozen quiz", quiz_type="multichoice",
        questions=[{"question": "Choose A", "correct_answer": "A", "options": ["A", "B"]}],
    )
    await db.quizzes_v2.insert_one(quiz.model_dump(by_alias=True))
    cohorts = CohortService(CohortRepository(db.cohorts, db.cohort_memberships), db.organization_memberships, db.users)
    repository = TrainingRunRepository(db.quizzes_v2, db.training_runs, db.training_assignments,
                                       db.training_audit_events, db.live_quiz_sessions,
                                       db.training_email_deliveries, db.organization_memberships,
                                       db.organizations, db.user_sessions)
    live = LiveQuizSessionService(LiveQuizSessionRepository(db.quizzes_v2, db.live_quiz_sessions),
                                  assignment_repository=repository)
    training = TrainingRunService(repository, live)
    service = AssignmentService(AssignmentRepository(repository, db.users, db.organization_memberships,
                                                     QuizRevisionRepository(db.quiz_revisions)),
                                training, CohortDeliveryAdapter(cohorts))
    cohort = await cohorts.create_cohort(CreateCohortRequest(kind="class", name="Class A"), contexts["owner"])
    await cohorts.set_member(cohort.id, SetCohortMemberRequest(user_id=ids["learner"]), contexts["owner"])
    storage = MemoryStorage()
    monkeypatch.setattr(limiter, "enabled", True)
    monkeypatch.setattr(limiter, "_headers_enabled", True)
    monkeypatch.setattr(limiter, "_storage_dead", False)
    monkeypatch.setattr(limiter, "_storage", storage)
    monkeypatch.setattr(limiter, "_limiter", FixedWindowRateLimiter(storage))
    state = SimpleNamespace(context=contexts["owner"], user=users["owner"])
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(cohorts_router, prefix="/api")
    app.include_router(assignments_router)
    app.include_router(progress_router)
    app.dependency_overrides[get_verified_user] = lambda: state.user
    app.dependency_overrides[get_active_organization_context] = lambda: state.context
    app.dependency_overrides[get_cohort_service] = lambda: cohorts
    app.dependency_overrides[get_assignment_service] = lambda: service
    return SimpleNamespace(db=db, org=org, ids=ids, contexts=contexts, users=users, quiz=quiz,
                           cohort=cohort, cohorts=cohorts, assignments=service, live=live,
                           app=app, state=state)


def payload(delivery, **changes):
    data = {"quiz_id": str(delivery.quiz.id), "cohort_id": delivery.cohort.id,
            "closes_at": datetime.now(timezone.utc) + timedelta(days=1), "max_attempts": 2}
    data.update(changes)
    return CreateAssignmentRequest(**data)


@pytest.mark.asyncio
async def test_frozen_roster_revision_submission_and_progress(delivery):
    d = delivery
    request = payload(d)
    assignment = await d.assignments.create(d.contexts["owner"], request, "cohort-create-01")
    await d.cohorts.set_member(d.cohort.id, SetCohortMemberRequest(user_id=d.ids["other"]), d.contexts["owner"])
    await d.db.quizzes_v2.update_one({"_id": d.quiz.id}, {"$set": {"title": "Changed",
        "questions": [{"question": "Changed question", "correct_answer": "B", "options": ["A", "B"]}]}})
    retry = await d.assignments.create(d.contexts["owner"], request, "cohort-create-01")
    assert retry["id"] == assignment["id"]
    assert retry["participant_count"] == 1
    assert await d.db.quiz_revisions.count_documents({}) == 1
    assert (await d.assignments.mine(d.contexts["other"]))["items"] == []
    started = await d.assignments.start(d.contexts["learner"], assignment["id"], d.users["learner"])
    session = await d.live.get_session_state(started["session_id"], started["participant_token"])
    assert session["delivery_kind"] == "quiz"
    assert session["question"]["question"] == "Choose A"
    await d.live.save_answer(started["session_id"], started["participant_token"], 0, "A")
    result = await d.live.submit_session(started["session_id"], started["participant_token"])
    assert result["percentage"] == 100
    progress = await d.assignments.detail(d.contexts["owner"], assignment["id"])
    assert progress["completion_percentage"] == 100
    assert progress["average_percentage"] == 100
    assert progress["outstanding_count"] == 0
    evidence = await d.assignments.attempt_detail(d.contexts["owner"], assignment["id"],
                                                 d.ids["learner"], started["session_id"])
    assert evidence["quiz_revision_id"] == assignment["quiz_revision_id"]


@pytest.mark.asyncio
async def test_route_contract_and_cross_tenant_guessed_ids(delivery):
    d = delivery
    async with AsyncClient(transport=ASGITransport(app=d.app), base_url="http://test") as client:
        response = await client.post("/api/v1/assignments", json=payload(d).model_dump(mode="json"),
                                     headers={"Idempotency-Key": "route-create-01"})
        assert response.status_code == 201, response.text
        assignment_id = response.json()["id"]
        assert (await client.get(f"/api/cohorts/{d.cohort.id}/progress")).json()["items"][0]["id"] == assignment_id
        foreign_organization = str(ObjectId())
        foreign_membership = {"organization_id": foreign_organization, "user_id": d.ids["learner"],
                              "role": "learner", "status": "active"}
        await d.db.organizations.insert_one({"_id": ObjectId(foreign_organization), "kind": "corporate", "status": "active"})
        await d.db.organization_memberships.insert_one(dict(foreign_membership))
        d.state.user = d.users["learner"]
        d.state.context = d.contexts["learner"].model_copy(update={
            "organization_id": foreign_organization, "membership": foreign_membership,
        })
        for path in (f"/api/cohorts/{d.cohort.id}", f"/api/v1/assignments/{assignment_id}",
                     f"/api/cohorts/{d.cohort.id}/progress"):
            response = await client.get(path)
            assert response.status_code == 404, (path, response.text)


@pytest.mark.asyncio
async def test_assignment_mutations_return_rate_headers_and_complete_real_delivery(delivery):
    d = delivery
    async with AsyncClient(transport=ASGITransport(app=d.app), base_url="http://test") as client:
        created = await client.post("/api/v1/assignments", json=payload(d).model_dump(mode="json"),
                                    headers={"Idempotency-Key": "limited-create-01"})
        assert created.status_code == 201, created.text
        run_id = created.json()["id"]
        d.state.user, d.state.context = d.users["learner"], d.contexts["learner"]
        started = await client.post(f"/api/v1/assignments/{run_id}/start")
        assert started.status_code == 200, started.text
        d.state.user, d.state.context = d.users["owner"], d.contexts["owner"]
        closed = await client.post(f"/api/v1/assignments/{run_id}/close", json={"confirm": True})
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == "closed"
        for response in (created, started, closed):
            assert int(response.headers["x-ratelimit-limit"]) > 0
            assert int(response.headers["x-ratelimit-remaining"]) >= 0
            assert "x-ratelimit-reset" in response.headers


@pytest.mark.asyncio
async def test_assignment_create_limit_blocks_before_duplicate_work(delivery):
    d = delivery
    body = payload(d).model_dump(mode="json")
    async with AsyncClient(transport=ASGITransport(app=d.app), base_url="http://test") as client:
        responses = [await client.post("/api/v1/assignments", json=body,
                                       headers={"Idempotency-Key": "rate-limit-retry-01"})
                     for _ in range(11)]
        assert all(response.status_code == 201 for response in responses[:10])
        assert responses[-1].status_code == 429
        assert responses[-1].json()["error"] == "rate_limit_exceeded"
        assert await d.db.training_runs.count_documents({}) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["future", "elapsed", "closed"])
async def test_http_start_checks_delivery_window_before_consuming_an_attempt(delivery, state):
    d = delivery
    changes = {"available_from": datetime.now(timezone.utc) + timedelta(hours=1)} if state == "future" else {}
    created = await d.assignments.create(d.contexts["owner"], payload(d, **changes), f"window-{state}-01")
    if state == "elapsed":
        await d.db.training_runs.update_one({"_id": ObjectId(created["id"])}, {
            "$set": {"closes_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
        })
    elif state == "closed":
        await d.assignments.close(d.contexts["owner"], created["id"])
    d.state.user, d.state.context = d.users["learner"], d.contexts["learner"]
    async with AsyncClient(transport=ASGITransport(app=d.app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/assignments/{created['id']}/start")
    assert response.status_code == 409, response.text
    recipient = await d.db.training_assignments.find_one({"training_run_id": created["id"]})
    assert recipient["attempts_used"] == 0
    assert await d.db.live_quiz_sessions.count_documents({}) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["available_from", "due_at", "closes_at"])
async def test_naive_assignment_dates_are_http_422_not_server_errors(delivery, field):
    d = delivery
    body = payload(d).model_dump(mode="json")
    body[field] = "2035-01-01T12:00:00"
    async with AsyncClient(transport=ASGITransport(app=d.app), base_url="http://test") as client:
        response = await client.post("/api/v1/assignments", json=body,
                                     headers={"Idempotency-Key": "invalid-date-01"})
    assert response.status_code == 422
    assert await d.db.training_runs.count_documents({}) == 0


@pytest.mark.asyncio
async def test_recipient_directory_skips_invalid_deleted_and_missing_users(delivery):
    d = delivery
    missing_id, deleted_id = str(ObjectId()), ObjectId()
    await d.db.users.insert_one({"_id": deleted_id, "username": "Deleted", "status": "deleted"})
    await d.db.organization_memberships.insert_many([
        {"organization_id": d.org, "user_id": user_id, "role": "learner", "status": "active"}
        for user_id in (missing_id, str(deleted_id), "bad")
    ])
    seen = []
    cursor = None
    while True:
        result = await d.assignments.recipient_options(d.contexts["owner"], limit=1, cursor=cursor)
        seen.extend(result["items"])
        cursor = result["next_cursor"]
        if cursor is None:
            break
    assert {row["user_id"] for row in seen} == set(d.ids.values())
    assert len(seen) == len(d.ids)
    assert all(set(row) == {"user_id", "name"} for row in seen)
    indexes = await d.db.organization_memberships.index_information()
    assert indexes["organization_member_options_cursor"]["key"] == [
        ("organization_id", 1), ("status", 1), ("_id", -1),
    ]


@pytest.mark.asyncio
async def test_mine_ignores_broken_references_and_refills_without_cross_tenant_data(delivery):
    d = delivery
    created = await d.assignments.create(d.contexts["owner"], payload(d), "mine-valid-01")
    recipient = await d.db.training_assignments.find_one({"training_run_id": created["id"]})
    original_run = await d.db.training_runs.find_one({"_id": ObjectId(created["id"])})
    foreign_run_id, deleted_run_id = ObjectId(), ObjectId()
    await d.db.training_runs.insert_many([
        {**original_run, "_id": foreign_run_id, "organization_id": str(ObjectId())},
        {**original_run, "_id": deleted_run_id, "status": "deleted", "idempotency_key": "deleted-run-01"},
    ])
    await d.db.training_assignments.insert_many([
        {**recipient, "_id": ObjectId(), "training_run_id": value}
        for value in ("bad", None, str(foreign_run_id), str(deleted_run_id))
    ])
    result = await d.assignments.mine(d.contexts["learner"], limit=1)
    assert [row["id"] for row in result["items"]] == [created["id"]]
    assert result["next_cursor"] is None


@pytest.mark.asyncio
async def test_assign_only_delegation_cannot_report_and_can_close_after_archive(delivery):
    d = delivery
    await d.cohorts.set_member(d.cohort.id, SetCohortMemberRequest(
        user_id=d.ids["facilitator"], role="facilitator", can_assign=True, can_report=False,
    ), d.contexts["owner"])
    assignment = await d.assignments.create(d.contexts["facilitator"], payload(d), "facilitator-create-01")
    assert assignment["can_manage"] is True
    assert assignment["can_report"] is False
    assert assignment["recipients"] == []
    assert "average_percentage" not in assignment or assignment["average_percentage"] is None
    with pytest.raises(HTTPException) as error:
        await d.assignments.attempts(d.contexts["facilitator"], assignment["id"], d.ids["learner"])
    assert error.value.status_code == 403
    await d.cohorts.archive_cohort(d.cohort.id, d.contexts["owner"])
    closed = await d.assignments.close(d.contexts["facilitator"], assignment["id"])
    assert closed["status"] == "closed"


@pytest.mark.asyncio
async def test_opening_time_and_revoked_membership_block_participant_token(delivery):
    d = delivery
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    scheduled = await d.assignments.create(d.contexts["owner"], payload(d, available_from=future), "scheduled-create-01")
    with pytest.raises(HTTPException) as error:
        await d.assignments.start(d.contexts["learner"], scheduled["id"], d.users["learner"])
    assert error.value.status_code == 409
    ready = await d.assignments.create(d.contexts["owner"], payload(d), "active-create-01")
    started = await d.assignments.start(d.contexts["learner"], ready["id"], d.users["learner"])
    await d.db.organization_memberships.update_one({"organization_id": d.org, "user_id": d.ids["learner"]},
                                                   {"$set": {"status": "suspended"}})
    with pytest.raises(HTTPException) as error:
        await d.live.get_session_state(started["session_id"], started["participant_token"])
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_resume_preserves_answer_timer_and_attempt_reservation(delivery):
    d = delivery
    assignment = await d.assignments.create(d.contexts["owner"], payload(d), "resume-create-01")
    first = await d.assignments.start(d.contexts["learner"], assignment["id"], d.users["learner"])
    await d.live.save_answer(first["session_id"], first["participant_token"], 0, "A")
    before = await d.db.live_quiz_sessions.find_one({"_id": ObjectId(first["session_id"])})
    resumed = await d.assignments.start(d.contexts["learner"], assignment["id"], d.users["learner"])
    after = await d.db.live_quiz_sessions.find_one({"_id": before["_id"]})
    recipient = await d.db.training_assignments.find_one({"training_run_id": assignment["id"]})
    assert resumed["session_id"] == first["session_id"]
    assert resumed["participant_token"] != first["participant_token"]
    assert after["expires_at"] == before["expires_at"]
    assert after["answers"] == before["answers"]
    assert recipient["attempts_used"] == 1
    result = await d.live.submit_session(resumed["session_id"], resumed["participant_token"])
    assert result["percentage"] == 100


@pytest.mark.asyncio
async def test_public_seed_template_creates_a_tenant_local_revision(delivery):
    d = delivery
    library_id = ObjectId()
    await d.db.organizations.insert_one({"_id": library_id, "kind": "personal",
        "status": "active", "system_key": "platform_library"})
    template = QuizDocumentV2(organization_id=str(library_id), title="Shared template",
        quiz_type="multichoice", source="seed", visibility="public",
        questions=[{"question": "Template question", "correct_answer": "A", "options": ["A", "B"]}])
    await d.db.quizzes_v2.insert_one(template.model_dump(by_alias=True))
    choices = await d.assignments.quizzes(d.contexts["owner"])
    assert str(template.id) in {item["id"] for item in choices["items"]}
    assignment = await d.assignments.create(d.contexts["owner"],
        payload(d, quiz_id=str(template.id)), "template-create-01")
    revision = await d.db.quiz_revisions.find_one({"_id": ObjectId(assignment["quiz_revision_id"])})
    assert revision["organization_id"] == d.org
    assert revision["quiz_id"] == str(template.id)
    started = await d.assignments.start(d.contexts["learner"], assignment["id"], d.users["learner"])
    state = await d.live.get_session_state(started["session_id"], started["participant_token"])
    assert state["question"]["question"] == "Template question"
    await d.db.organizations.update_one({"_id": library_id}, {"$set": {"status": "suspended"}})
    with pytest.raises(HTTPException) as error:
        await d.assignments.create(d.contexts["owner"], payload(d, quiz_id=str(template.id)), "template-create-02")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_closed_list_and_detail_keep_the_same_frozen_progress(delivery):
    d = delivery
    assignment = await d.assignments.create(d.contexts["owner"], payload(d), "closure-create-01")
    started = await d.assignments.start(d.contexts["learner"], assignment["id"], d.users["learner"])
    await d.live.save_answer(started["session_id"], started["participant_token"], 0, "A")
    await d.live.submit_session(started["session_id"], started["participant_token"])
    closed = await d.assignments.close(d.contexts["owner"], assignment["id"])
    await d.db.training_assignments.update_many({"training_run_id": assignment["id"]},
        {"$set": {"latest_percentage": 0, "latest_score": 0}})
    detail = await d.assignments.detail(d.contexts["owner"], assignment["id"])
    listed = (await d.assignments.list(d.contexts["owner"]))["items"][0]
    own = (await d.assignments.mine(d.contexts["learner"]))["items"][0]
    assert closed["average_percentage"] == detail["average_percentage"] == listed["average_percentage"] == 100
    assert detail["recipients"][0]["latest_percentage"] == own["latest_percentage"] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("register", [None, {}, "invalid"])
async def test_malformed_retained_register_is_a_controlled_503(delivery, register):
    d = delivery
    assignment = await d.assignments.create(d.contexts["owner"], payload(d), "malformed-create-01")
    await d.assignments.close(d.contexts["owner"], assignment["id"])
    await d.db.training_audit_events.update_one({"training_run_id": assignment["id"], "event_type": "run_closed"},
        {"$set": {"payload.completion_register": register}})
    with pytest.raises(HTTPException) as error:
        await d.assignments.detail(d.contexts["owner"], assignment["id"])
    assert error.value.status_code == 503
    with pytest.raises(HTTPException) as error:
        await d.assignments.mine(d.contexts["learner"])
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_revision_schema_setup_is_safe_when_workers_start_together(delivery):
    import asyncio

    await delivery.db.drop_collection("quiz_revisions")
    await asyncio.gather(*(ensure_assignment_collections(delivery.db) for _ in range(4)))
    indexes = await delivery.db.quiz_revisions.index_information()
    assert indexes["organization_quiz_revision_content"]["unique"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["suspended", "deleted"])
async def test_platform_account_disable_revokes_private_assignment_token(delivery, status):
    d = delivery
    assignment = await d.assignments.create(d.contexts["owner"], payload(d), "account-disable-01")
    started = await d.assignments.start(d.contexts["learner"], assignment["id"], d.users["learner"])
    await d.db.users.update_one({"_id": ObjectId(d.ids["learner"])}, {"$set": {"status": status}})
    with pytest.raises(HTTPException) as error:
        await d.live.get_session_state(started["session_id"], started["participant_token"])
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_write_from_a_stale_workspace_form_is_rejected_before_creation(delivery):
    d = delivery
    next_org = str(ObjectId())
    await d.db.organizations.insert_one({"_id": ObjectId(next_org), "kind": "school", "status": "active"})
    await d.db.organization_memberships.insert_one({"organization_id": next_org,
        "user_id": d.ids["owner"], "role": "owner", "status": "active"})
    await d.db.user_sessions.update_one({"session_id": d.users["owner"].session_id},
        {"$set": {"active_organization_id": next_org}})
    d.state.user.role = "user"
    d.state.user.default_organization_id = d.org
    d.app.dependency_overrides.pop(get_active_organization_context)
    d.app.dependency_overrides[get_current_user] = lambda: d.state.user
    d.app.dependency_overrides[get_organizations_collection] = lambda: d.db.organizations
    d.app.dependency_overrides[get_organization_memberships_collection] = lambda: d.db.organization_memberships
    d.app.dependency_overrides[get_user_sessions_collection] = lambda: d.db.user_sessions
    async with AsyncClient(transport=ASGITransport(app=d.app), base_url="http://test") as client:
        response = await client.post("/api/cohorts", json={"kind": "class", "name": "Stale form"},
            headers={"X-Organization-ID": d.org})
        assert response.status_code == 409, response.text
        assert await d.db.cohorts.count_documents({"name": "Stale form"}) == 0
        response = await client.post("/api/cohorts", json={"kind": "class", "name": "Current form"},
            headers={"X-Organization-ID": next_org})
        assert response.status_code == 201, response.text
        assert response.json()["organization_id"] == next_org
