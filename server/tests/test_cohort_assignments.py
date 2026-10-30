from copy import deepcopy
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError
import pytest

from server.app.assignments.models import CreateAssignmentRequest
from server.app.assignments.revisions import QuizRevisionRepository
from server.app.assignments.service import AssignmentService
from server.app.assignments.statistics import add_assignment_closure_evidence, recipient_statistics
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.services.live_session_service import LiveQuizSessionService, _hash_token
from server.app.quiz.services.training_run_service import TrainingRunService
from server.app.quiz.utils.training_completion import build_closure_payload
from server.tests.test_training_run_service import CreateRunRepository, FakeTrainingSessionRepository, ConcurrentAssignmentsCollection


ORG, ACTOR, MEMBER, COHORT = (str(ObjectId()) for _ in range(4))


def context(role="owner", actor=ACTOR, org=ORG):
    return OrganizationContext(
        organization_id=org, organization_kind="school", membership_role=role,
        membership={"organization_id": org, "user_id": actor, "role": role, "status": "active"},
        principal=OrganizationPrincipal(user_id=actor, session_id="auth-session"),
    )


def payload(**changes):
    return CreateAssignmentRequest(**{
        "quiz_id": str(ObjectId()), "cohort_id": COHORT,
        "closes_at": datetime.now(timezone.utc) + timedelta(days=2), **changes,
    })


class EngineRepository(CreateRunRepository):
    def __init__(self):
        super().__init__()
        self.quiz.update(organization_id=ORG, owner_user_id=ACTOR, created_by_user_id=ACTOR)

    async def get_run_by_idempotency_key(self, owner, key, organization_id=None):
        if organization_id != ORG:
            return None
        return await super().get_run_by_idempotency_key(owner, key)

    async def get_quiz_for_organization(self, quiz_id, org):
        return self.quiz if org == ORG else None


class Revisions:
    def __init__(self):
        self.calls = 0

    async def snapshot(self, org, quiz, actor):
        self.calls += 1
        return {"_id": ObjectId(), "snapshot": TrainingRunService._quiz_snapshot(quiz)}


def setup_service():
    engine = EngineRepository()
    training = TrainingRunService(engine, None)
    repository = SimpleNamespace(
        training=engine, revisions=Revisions(),
        active_recipients=AsyncMock(return_value=[{"user_id": MEMBER, "email": "learner@example.com", "name": "Learner"}]),
        library_quiz=AsyncMock(return_value=None),
    )
    cohorts = SimpleNamespace(
        get_cohort=AsyncMock(return_value={"_id": ObjectId(COHORT), "status": "active", "organization_id": ORG}),
        recipient_ids=AsyncMock(return_value=[MEMBER]), can=AsyncMock(return_value=True),
    )
    service = AssignmentService(repository, training, cohorts)
    service.detail = AsyncMock(side_effect=lambda ctx, run_id: {"id": run_id})
    return service, repository, cohorts, engine


@pytest.mark.asyncio
async def test_create_reuses_training_engine_and_snapshots_roster_and_revision():
    service, repository, cohorts, engine = setup_service()
    request = payload()
    result = await service.create(context(), request, "request-one")
    run = engine.created_run
    assert result["id"] == str(run["_id"])
    assert run["kind"] == run["delivery_kind"] == "quiz"
    assert run["recipient_snapshot"][0]["user_id"] == MEMBER
    assert ObjectId.is_valid(run["quiz_revision_id"])
    assert run["provisioning_complete"] is True
    assert engine.assignments[0]["recipient_user_id"] == MEMBER
    assert engine.assignments[0]["quiz_revision_id"] == run["quiz_revision_id"]
    assert engine.assignments[0]["delivery_kind"] == "quiz"
    assert "access_code" not in run
    cohorts.recipient_ids.assert_awaited_once()


@pytest.mark.asyncio
async def test_idempotent_retry_never_reexpands_roster_or_rereads_mutated_quiz():
    service, repository, cohorts, engine = setup_service()
    request = payload()
    first = await service.create(context(), request, "request-one")
    original = deepcopy(engine.created_run["quiz_snapshot"])
    engine.quiz["questions"] = [{"question": "Changed", "answer": "Wrong"}]
    cohorts.recipient_ids.return_value = [str(ObjectId())]
    repository.active_recipients.side_effect = AssertionError("Must not refresh an existing roster")
    second = await service.create(context(), request, "request-one")
    assert second == first
    assert engine.created_run["quiz_snapshot"] == original
    assert len(engine.assignments) == 1
    assert repository.revisions.calls == 1
    cohorts.recipient_ids.assert_awaited_once()


@pytest.mark.asyncio
async def test_interrupted_provisioning_resumes_original_roster():
    service, repository, cohorts, engine = setup_service()
    request = payload()
    original = engine.mark_run_open
    engine.mark_run_open = AsyncMock(side_effect=RuntimeError("Transient database failure"))
    with pytest.raises(RuntimeError):
        await service.create(context(), request, "request-one")
    assert engine.created_run["status"] == "provisioning"
    cohorts.recipient_ids.return_value = [str(ObjectId())]
    engine.mark_run_open = original
    await service.create(context(), request, "request-one")
    assert len(engine.assignments) == 1
    assert engine.assignments[0]["recipient_user_id"] == MEMBER
    assert repository.revisions.calls == 1


@pytest.mark.asyncio
async def test_changed_intent_with_same_idempotency_key_conflicts():
    service, repository, cohorts, engine = setup_service()
    request = payload()
    await service.create(context(), request, "request-one")
    with pytest.raises(HTTPException) as caught:
        await service.create(context(), request.model_copy(update={"title": "Another assignment"}), "request-one")
    assert caught.value.status_code == 409


@pytest.mark.asyncio
async def test_delegate_assignment_permission_is_independent_of_reporting():
    service, repository, cohorts, engine = setup_service()
    cohorts.can.side_effect = lambda ctx, cohort, capability: capability == "assign"
    await service.create(context("facilitator"), payload(), "request-one")
    with pytest.raises(HTTPException) as caught:
        await service._require(context("facilitator"), engine.created_run, "report")
    assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_archived_cohort_rejects_new_assignment_before_durable_writes():
    service, repository, cohorts, engine = setup_service()
    cohorts.get_cohort.return_value["status"] = "archived"
    with pytest.raises(HTTPException) as caught:
        await service.create(context(), payload(), "request-one")
    assert caught.value.status_code == 409
    assert engine.created_run is None
    assert repository.revisions.calls == 0


@pytest.mark.asyncio
async def test_cross_organization_quiz_cannot_be_assigned():
    service, repository, cohorts, engine = setup_service()
    with pytest.raises(HTTPException) as caught:
        await service.create(context(org=str(ObjectId())), payload(), "request-one")
    assert caught.value.status_code == 404
    assert engine.created_run is None


@pytest.mark.asyncio
async def test_public_platform_library_quiz_is_frozen_into_active_organization():
    service, repository, cohorts, engine = setup_service()
    library_id = str(ObjectId())
    library_quiz = {**engine.quiz, "organization_id": library_id, "owner_user_id": None,
        "created_by_user_id": None, "visibility": "public", "source": "seed"}
    engine.get_quiz_for_organization = AsyncMock(return_value=None)
    repository.library_quiz.return_value = library_quiz
    await service.create(context(), payload(), "library-quiz")
    assert engine.created_run["organization_id"] == ORG
    assert engine.created_run["owner_user_id"] == ACTOR
    assert engine.created_run["quiz_snapshot"]["questions"] == library_quiz["questions"]
    assert engine.assignments[0]["organization_id"] == ORG
    repository.library_quiz.assert_awaited_once()


@pytest.mark.parametrize("changes", [
    {"cohort_id": None, "recipient_user_ids": []},
    {"recipient_user_ids": [MEMBER]},
    {"available_from": datetime.now(timezone.utc).replace(tzinfo=None)},
    {"available_from": datetime.now(timezone.utc) + timedelta(days=3)},
    {"max_attempts": 3},
    {"title": "Unsafe\nTitle"},
])
def test_request_rejects_invalid_target_schedule_and_retry_policy(changes):
    with pytest.raises(ValidationError):
        payload(**changes)


@pytest.mark.parametrize("value", [True, False, 1.0, "2"])
def test_retry_policy_does_not_coerce_boolean_or_string_limits(value):
    with pytest.raises(ValidationError):
        payload(max_attempts=value)


def test_fingerprint_normalizes_threshold_and_recipient_order():
    first = payload(cohort_id=None, recipient_user_ids=[ACTOR, MEMBER], passing_threshold_percentage=80)
    second = first.model_copy(update={"passing_threshold_percentage": 80.0})
    assert AssignmentService.fingerprint(first, ORG) == AssignmentService.fingerprint(second, ORG)


@pytest.mark.asyncio
async def test_revision_content_is_frozen_and_tenant_local():
    collection = SimpleNamespace(find_one_and_update=AsyncMock(side_effect=lambda query, update, **kwargs: deepcopy(update["$setOnInsert"])))
    repository = QuizRevisionRepository(collection)
    quiz = {"_id": ObjectId(), "title": "Original", "quiz_type": "multichoice", "questions": [{"question": "Original", "answer": "A"}]}
    first = await repository.snapshot(ORG, quiz, ACTOR)
    quiz["questions"][0]["question"] = "Edited"
    second = await repository.snapshot(ORG, quiz, ACTOR)
    assert first["snapshot"]["questions"][0]["question"] == "Original"
    assert first["content_hash"] != second["content_hash"]
    assert collection.find_one_and_update.await_args.args[0]["organization_id"] == ORG


def test_progress_uses_latest_submitted_percentage_even_during_retry():
    submitted_at = datetime.now(timezone.utc)
    records = [
        {"status": "in_progress", "completed_at": submitted_at, "latest_score": 1, "latest_percentage": 50},
        {"status": "completed", "completed_at": submitted_at, "latest_score": 9, "latest_percentage": 90},
        {"status": "assigned"},
    ]
    result = recipient_statistics(records)
    assert result == {"participant_count": 3, "completed_count": 2, "outstanding_count": 1,
        "completion_percentage": 66.67, "average_percentage": 70.0}


def test_closure_keeps_percentage_summary_and_recipient_identity_frozen():
    timestamp = datetime.now(timezone.utc)
    run = {"_id": ObjectId(), "delivery_kind": "quiz", "quiz_revision_id": str(ObjectId()), "cohort_id": COHORT}
    assignment = {"_id": ObjectId(), "recipient_user_id": MEMBER, "status": "completed", "latest_percentage": 75, "latest_score": 3, "completed_at": timestamp}
    closure = add_assignment_closure_evidence(build_closure_payload(run, [assignment], []), run, [assignment])
    assignment["latest_percentage"] = 0
    assert closure["assignment_summary"]["average_percentage"] == 75
    assert closure["completion_register"][0]["recipient_user_id"] == MEMBER
    assert closure["run"]["quiz_revision_id"] == run["quiz_revision_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["state", "save", "submit"])
async def test_suspended_recipient_cannot_use_existing_participant_token(operation):
    session = {"_id": ObjectId(), "delivery_kind": "quiz", "status": "submitted", "participant_token_hash": _hash_token("secret")}
    repository = SimpleNamespace(get_session=AsyncMock(return_value=session))
    assignments = SimpleNamespace(delivery_participant_active=AsyncMock(return_value=False))
    service = LiveQuizSessionService(repository, assignment_repository=assignments)
    with pytest.raises(HTTPException) as caught:
        if operation == "state":
            await service.get_session_state(str(session["_id"]), "secret")
        elif operation == "save":
            await service.save_answer(str(session["_id"]), "secret", 0, "A")
        else:
            await service.submit_session(str(session["_id"]), "secret")
    assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_generic_session_persists_assignment_revision_and_organization():
    quiz = {"_id": ObjectId(), "organization_id": ORG, "created_by_user_id": ACTOR,
        "delivery_kind": "quiz", "quiz_revision_id": str(ObjectId()), "questions": [{"question": "Q", "answer": "A"}]}
    repository = FakeTrainingSessionRepository(quiz)
    service = LiveQuizSessionService(repository)
    run_id, recipient_id = str(ObjectId()), str(ObjectId())
    await service.start_session_for_quiz(quiz, participant_name="Learner", participant_email="learner@example.com",
        time_limit_minutes=20, training_run_id=run_id, training_assignment_id=recipient_id,
        user_id=MEMBER, quiz_snapshot=quiz, organization_session_id="auth-session")
    session = repository.session
    assert session["organization_id"] == ORG
    assert session["assignment_id"] == run_id
    assert session["quiz_revision_id"] == quiz["quiz_revision_id"]
    assert session["organization_session_id"] == "auth-session"


@pytest.mark.asyncio
async def test_resume_rotates_token_without_resetting_timer_or_answers():
    timestamp = datetime.now(timezone.utc)
    session = {"_id": ObjectId(), "delivery_kind": "quiz", "organization_id": ORG, "user_id": MEMBER,
        "training_run_id": str(ObjectId()), "training_assignment_id": str(ObjectId()),
        "participant_token_hash": _hash_token("old"), "started_at": timestamp - timedelta(minutes=3),
        "expires_at": timestamp + timedelta(minutes=17), "time_limit_minutes": 20,
        "duration_seconds": 1200, "status": "active", "answers": [{"question_index": 0, "selected_answer": "A"}]}
    async def rotate(original, token_hash, auth_session_id, current_time):
        assert original["answers"] == session["answers"]
        return {**original, "participant_token_hash": token_hash}
    assignments = SimpleNamespace(
        delivery_participant_active=AsyncMock(return_value=True),
        get_run=AsyncMock(return_value={"status": "open", "closes_at": timestamp + timedelta(days=1)}),
        rotate_assignment_session_token=AsyncMock(side_effect=rotate),
    )
    service = LiveQuizSessionService(None, assignment_repository=assignments)
    result = await service.resume_assigned_session(session, user_id=MEMBER, organization_session_id="new-login")
    assert result["started_at"] == session["started_at"]
    assert result["expires_at"] == session["expires_at"]
    assert _hash_token(result["participant_token"]) != session["participant_token_hash"]
    assert 0 < result["remaining_seconds"] < 1200


@pytest.mark.asyncio
async def test_attempt_detail_requires_exact_assignment_recipient_and_reporting():
    run_id, recipient_id, session_id = (str(ObjectId()) for _ in range(3))
    run = {"_id": ObjectId(run_id), "organization_id": ORG, "cohort_id": COHORT}
    repository = SimpleNamespace(
        run=AsyncMock(return_value=run),
        recipient=AsyncMock(return_value={"_id": ObjectId(recipient_id)}),
        attempt=AsyncMock(return_value=None),
    )
    cohorts = SimpleNamespace(can=AsyncMock(return_value=True))
    service = AssignmentService(repository, None, cohorts)
    with pytest.raises(HTTPException) as caught:
        await service.attempt_detail(context("facilitator"), run_id, MEMBER, session_id)
    assert caught.value.status_code == 404
    cohorts.can.assert_awaited_once_with(context("facilitator"), COHORT, "attempt")
    repository.attempt.assert_awaited_once_with(ORG, run_id, recipient_id, MEMBER, session_id)


@pytest.mark.asyncio
async def test_report_only_delegate_cannot_close_assignment():
    run = {"_id": ObjectId(), "organization_id": ORG, "cohort_id": COHORT, "status": "open"}
    repository = SimpleNamespace(run=AsyncMock(return_value=run))
    cohorts = SimpleNamespace(can=AsyncMock(side_effect=lambda ctx, cohort, capability: capability == "report"))
    training = SimpleNamespace(_close_run=AsyncMock())
    service = AssignmentService(repository, training, cohorts)
    with pytest.raises(HTTPException) as caught:
        await service.close(context("facilitator"), str(run["_id"]))
    assert caught.value.status_code == 403
    training._close_run.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["learner", "guardian", "author"])
async def test_recipient_picker_rejects_non_assigning_roles(role):
    repository = SimpleNamespace(memberships=None)
    service = AssignmentService(repository, None, None)
    with pytest.raises(HTTPException) as caught:
        await service.recipient_options(context(role))
    assert caught.value.status_code == 403


@pytest.mark.asyncio
async def test_facilitator_recipient_picker_only_returns_ids_and_names():
    cursor = SimpleNamespace(to_list=AsyncMock(return_value=[{
        "_id": ObjectId(), "user_id": MEMBER, "_user": [{"full_name": "Learner", "email": "private@example.com"}],
    }]))
    captured = []
    def aggregate(pipeline):
        captured.append(pipeline)
        return cursor
    repository = SimpleNamespace(memberships=SimpleNamespace(aggregate=aggregate), users=SimpleNamespace(name="users"))
    service = AssignmentService(repository, None, None)
    result = await service.recipient_options(context("facilitator"))
    assert result["items"] == [{"user_id": MEMBER, "name": "Learner"}]
    assert captured[0][0]["$match"] == {"organization_id": ORG, "status": "active"}


@pytest.mark.asyncio
async def test_quiz_level_reports_and_events_exclude_cohort_assignment_sessions():
    session = {"_id": ObjectId(), "delivery_kind": "quiz", "organization_id": ORG,
        "quiz_id": str(ObjectId()), "status": "submitted", "submitted_at": datetime.now(timezone.utc)}
    repository = SimpleNamespace(
        list_quiz_sessions=AsyncMock(return_value=[session]), get_session=AsyncMock(return_value=session),
    )
    broadcaster = SimpleNamespace(publish=AsyncMock())
    service = LiveQuizSessionService(repository, broadcaster=broadcaster)
    assert await service._list_quiz_sessions(session["quiz_id"], ORG) == []
    await service._publish_participant_event(session["quiz_id"], str(session["_id"]), "participant_submitted")
    broadcaster.publish.assert_not_awaited()
    with pytest.raises(HTTPException) as caught:
        await service.get_attempt_detail(session["quiz_id"], str(session["_id"]), ACTOR,
            authorized_quiz={"_id": ObjectId(session["quiz_id"]), "organization_id": ORG})
    assert caught.value.status_code == 404


@pytest.mark.asyncio
async def test_assignment_opening_boundary_prevents_session_or_retry_reservation():
    timestamp = datetime.now(timezone.utc)
    assignment_id, run_id = str(ObjectId()), str(ObjectId())
    repository = SimpleNamespace(
        bind_assignments_to_user=AsyncMock(return_value=[]),
        get_assignment_for_recipient=AsyncMock(return_value={"_id": ObjectId(assignment_id), "recipient_user_id": MEMBER, "training_run_id": run_id}),
        get_run=AsyncMock(return_value={"organization_id": ORG, "status": "open", "available_from": timestamp + timedelta(hours=1), "closes_at": timestamp + timedelta(days=2)}),
        reserve_attempt=AsyncMock(),
    )
    service = TrainingRunService(repository, None)
    with pytest.raises(HTTPException) as caught:
        await service.start_assignment(assignment_id, SimpleNamespace(id=MEMBER, email="learner@example.com"), organization_id=ORG)
    assert caught.value.status_code == 409
    assert "not available" in caught.value.detail
    repository.reserve_attempt.assert_not_awaited()


@pytest.mark.asyncio
async def test_two_tabs_cannot_reserve_parallel_attempts_with_two_attempt_policy():
    collection = ConcurrentAssignmentsCollection({
        "_id": ObjectId(), "recipient_user_id": MEMBER, "max_attempts": 2,
        "attempts_used": 0, "status": "assigned",
    })
    repository = TrainingRunRepository(None, None, collection, None)
    results = await asyncio.gather(*[
        repository.reserve_attempt(str(collection.document["_id"]), MEMBER, datetime.now(timezone.utc))
        for _ in range(2)
    ])
    assert sum(row is not None for row in results) == 1
    assert collection.document["attempts_used"] == 1


@pytest.mark.asyncio
async def test_start_resumes_live_session_without_consuming_another_attempt():
    run_id, recipient_id, session_id = (str(ObjectId()) for _ in range(3))
    run = {"_id": ObjectId(run_id), "organization_id": ORG}
    session = {"_id": ObjectId(session_id), "status": "active", "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)}
    repository = SimpleNamespace(
        run=AsyncMock(return_value=run),
        recipient=AsyncMock(return_value={"_id": ObjectId(recipient_id), "status": "in_progress", "active_session_id": session_id}),
        attempt=AsyncMock(return_value=session),
    )
    live = SimpleNamespace(resume_assigned_session=AsyncMock(return_value={"session_id": session_id}))
    training = SimpleNamespace(live_quiz_service=live, start_assignment=AsyncMock())
    service = AssignmentService(repository, training, None)
    assert await service.start(context(actor=MEMBER), run_id, SimpleNamespace(id=MEMBER)) == {"session_id": session_id}
    training.start_assignment.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_attempt_is_finalized_before_retry_is_reserved():
    run_id, recipient_id, session_id = (str(ObjectId()) for _ in range(3))
    run = {"_id": ObjectId(run_id), "organization_id": ORG}
    session = {"_id": ObjectId(session_id), "status": "active", "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}
    recipient = {"_id": ObjectId(recipient_id), "status": "in_progress", "active_session_id": session_id}
    repository = SimpleNamespace(run=AsyncMock(return_value=run), recipient=AsyncMock(return_value=recipient), attempt=AsyncMock(return_value=session))
    sequence = []
    async def finalize(*args, **kwargs):
        sequence.append("finalized")
    async def start(*args, **kwargs):
        sequence.append("reserved")
        return {"session_id": "next-session"}
    live = SimpleNamespace(
        _ensure_training_expiry_can_finalize=AsyncMock(), _get_session_quiz=AsyncMock(return_value={"questions": [{}]}),
        _finalize_session=AsyncMock(side_effect=finalize),
    )
    training = SimpleNamespace(live_quiz_service=live, start_assignment=AsyncMock(side_effect=start))
    service = AssignmentService(repository, training, None)
    await service.start(context(actor=MEMBER), run_id, SimpleNamespace(id=MEMBER))
    assert sequence == ["finalized", "reserved"]


@pytest.mark.asyncio
async def test_malformed_frozen_summary_cannot_override_identity_or_hide_other_runs():
    healthy, malformed = ObjectId(), ObjectId()
    runs = [{"_id": identifier, "organization_id": ORG, "status": "closed", "title": "Original"} for identifier in (healthy, malformed)]
    good = {"participant_count": 2, "completed_count": 1, "outstanding_count": 1, "completion_percentage": 50.0, "average_percentage": 80.0}
    repository = SimpleNamespace(summaries=AsyncMock(return_value={
        str(healthy): good, str(malformed): {**good, "organization_id": "attacker", "id": "attacker"},
    }))
    summaries = await AssignmentService(repository, None, None)._summaries(context(), runs)
    assert summaries[0]["summary_availability"] == "available"
    assert summaries[0]["average_percentage"] == 80
    assert summaries[1]["summary_availability"] == "unavailable"
    assert summaries[1]["id"] == str(malformed)
    assert summaries[1]["organization_id"] == ORG


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"participant_count": -1}, {"completed_count": 4},
    {"average_percentage": float("nan")}, {"completion_percentage": 75},
])
async def test_invalid_closure_statistics_are_unavailable(bad):
    run = {"_id": ObjectId(), "organization_id": ORG, "status": "closed"}
    stats = {"participant_count": 2, "completed_count": 1, "outstanding_count": 1, "completion_percentage": 50.0, "average_percentage": 80.0, **bad}
    service = AssignmentService(SimpleNamespace(summaries=AsyncMock(return_value={str(run["_id"]): stats})), None, None)
    assert (await service._summaries(context(), [run]))[0]["summary_availability"] == "unavailable"


@pytest.mark.parametrize("record", [{}, {"assignment_id": "bad", "status": "completed"}, {"interpretation_error": True}])
def test_malformed_frozen_recipient_is_a_controlled_503(record):
    run = {"closes_at": datetime.now(timezone.utc), "created_at": datetime.now(timezone.utc), "time_limit_minutes": 20, "status": "closed"}
    with pytest.raises(HTTPException) as caught:
        AssignmentService._recipient(record, run)
    assert caught.value.status_code == 503
