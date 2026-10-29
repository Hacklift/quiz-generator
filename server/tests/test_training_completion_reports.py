import csv
import io
from typing import get_args
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from server.app.core.dependencies import get_current_user
from server.app.core.rate_limiter import limiter
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.quiz.routes import training_runs
from server.app.quiz.schemas.training_runs import CreateTrainingRunRequest
from server.app.quiz.services.training_run_service import TrainingRunService
from server.app.quiz.utils.training_completion import (
    build_closure_payload, completion_outcome, completion_report_csv, completion_row,
    completion_summary, assignment_snapshot, MAX_COMPLETION_REPORT_ROWS,
    CompletionEvidenceError, SHARED_SESSION_STATES, closed_run_metadata,
)


def run_document():
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(), "quiz_id": str(ObjectId()), "owner_user_id": "owner-1",
        "title": "Safety training", "kind": "compliance", "purpose": "health_and_safety",
        "status": "open", "access_mode": "assigned_only", "time_limit_minutes": 20,
        "passing_threshold_percentage": 80, "closes_at": now + timedelta(days=7),
        "created_at": now, "quiz_snapshot": {"questions": [{"question": "Q", "answer": "A"}]},
    }


def assignments():
    return [{
        "_id": ObjectId(), "recipient_email": "learner@example.com", "status": "completed",
        "latest_score": 4, "latest_percentage": 80, "completed_at": datetime.now(timezone.utc),
        "attempts_used": 1, "max_attempts": 2,
    }, {
        "_id": ObjectId(), "recipient_email": "absent@example.com", "status": "assigned",
        "attempts_used": 0, "max_attempts": 2,
    }]


def report_service(run=None, rows=None):
    run = run or run_document()
    rows = rows if rows is not None else assignments()

    async def get_run_for_owner(identifier, owner_user_id, organization_id, allow_legacy_personal):
        legacy = run.get("organization_id") is None and allow_legacy_personal
        if (
            identifier == str(run["_id"])
            and owner_user_id == run["owner_user_id"]
            and (run.get("organization_id") == organization_id or legacy)
        ):
            return deepcopy(run)
        return None

    async def get_run_for_organization(identifier, organization_id):
        if identifier == str(run["_id"]) and run.get("organization_id") == organization_id:
            return deepcopy(run)
        return None

    repository = SimpleNamespace(
        get_run=AsyncMock(side_effect=lambda identifier: deepcopy(run) if identifier == str(run["_id"]) else None),
        get_run_for_owner=AsyncMock(side_effect=get_run_for_owner),
        get_run_for_organization=AsyncMock(side_effect=get_run_for_organization),
        list_assignments_for_run=AsyncMock(return_value=rows),
        list_sessions_for_run=AsyncMock(return_value=[]),
        get_closure_audit=AsyncMock(return_value=None),
        get_run_activity_summary=AsyncMock(return_value=completion_summary([
            completion_row(assignment_snapshot(row), 80) for row in rows
        ])),
        get_closure_activity_summary=AsyncMock(return_value=completion_summary([
            completion_row(assignment_snapshot(row), 80) for row in rows
        ])),
    )
    return TrainingRunService(repository, SimpleNamespace()), repository, run


@pytest.mark.parametrize("percentage,threshold,outcome", [
    (80, 80, "passed"), (79.99, 80, "failed"), (0, 0, "passed"),
    (100, 100, "passed"), (99.9, 100, "failed"), (80, None, "unknown"),
    (None, 80, "unknown"), (float("nan"), 80, "unknown"),
])
def test_threshold_boundary_and_unknown_legacy_results(percentage, threshold, outcome):
    assert completion_outcome("completed", percentage, threshold) == outcome
    assert completion_outcome("incomplete", percentage, threshold) == "not_completed"


@pytest.mark.parametrize("threshold", [-1, 101, float("nan"), float("inf"), True, None, "invalid"])
def test_creation_rejects_invalid_thresholds(threshold):
    with pytest.raises(ValidationError):
        CreateTrainingRunRequest(
            quiz_id="quiz-1", closes_at=datetime.now(timezone.utc) + timedelta(days=1),
            recipient_emails=["learner@example.com"], passing_threshold_percentage=threshold,
        )


def test_custom_threshold_changes_creation_intent_without_breaking_default_retries():
    request = CreateTrainingRunRequest(
        quiz_id="quiz-1", closes_at=datetime.now(timezone.utc) + timedelta(days=1),
        recipient_emails=["learner@example.com"],
    )
    explicit_default = request.model_copy(update={"passing_threshold_percentage": 80.0})
    custom = request.model_copy(update={"passing_threshold_percentage": 70.0})
    assert request.passing_threshold_percentage == 80
    assert TrainingRunService._request_fingerprint(request) == TrainingRunService._request_fingerprint(explicit_default)
    assert TrainingRunService._request_fingerprint(request) != TrainingRunService._request_fingerprint(custom)


@pytest.mark.parametrize("threshold", [80, 80.0, 70, 70.0, 0, 0.0])
def test_numeric_threshold_retries_have_stable_server_fingerprints(threshold):
    request = CreateTrainingRunRequest(
        quiz_id="quiz-1", closes_at=datetime.now(timezone.utc) + timedelta(days=1),
        recipient_emails=["learner@example.com"], passing_threshold_percentage=threshold,
    )
    retry = request.model_copy(update={"passing_threshold_percentage": float(threshold)})
    assert TrainingRunService._request_fingerprint(request) == TrainingRunService._request_fingerprint(retry)


@pytest.mark.asyncio
async def test_created_run_persists_custom_threshold_with_existing_creation_flow():
    from server.tests.test_training_run_service import CreateRunRepository

    repository = CreateRunRepository()
    service = TrainingRunService(repository, SimpleNamespace())
    request = CreateTrainingRunRequest(
        quiz_id=str(repository.quiz["_id"]), closes_at=datetime.now(timezone.utc) + timedelta(days=1),
        recipient_emails=["learner@example.com"], passing_threshold_percentage=70,
    )
    result = await service.create_run(request, "owner-1", "threshold-test-1")
    assert result["passing_threshold_percentage"] == 70
    assert repository.created_run["passing_threshold_percentage"] == 70


@pytest.mark.asyncio
async def test_provisional_register_includes_all_assignees_and_current_outcomes():
    service, _, run = report_service()
    report = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert report["report_is_final"] is False
    assert report["passing_threshold_percentage"] == 80
    assert [row["outcome"] for row in report["completion_register"]] == ["passed", "not_completed"]
    csv_rows = list(csv.DictReader(io.StringIO(completion_report_csv(report, generated_at=datetime.now(timezone.utc)))))
    assert csv_rows[0]["record_status"] == "provisional"
    assert csv_rows[1]["completion_status"] == "not_started"
    assert csv_rows[0]["completed_at_utc"].endswith("+00:00")


@pytest.mark.asyncio
async def test_closed_report_uses_snapshot_not_mutated_live_records():
    rows = assignments()
    service, repository, run = report_service(rows=rows)
    payload = build_closure_payload(run, rows, [])
    run.update(status="closed", passing_threshold_percentage=99, title="Changed after closure")
    rows[0].update(latest_percentage=0, latest_score=0)
    repository.get_closure_audit.return_value = {"payload": payload, "occurred_at": run["created_at"]}
    report = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert report["report_is_final"] is True
    assert report["title"] == "Safety training"
    assert report["passing_threshold_percentage"] == 80
    assert report["completion_register"][0]["latest_percentage"] == 80
    assert report["completion_register"][0]["outcome"] == "passed"
    repository.list_assignments_for_run.assert_not_awaited()
    repository.list_sessions_for_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_snapshot_does_not_invent_default_threshold_or_rewrite_evidence():
    service, repository, run = report_service()
    run["status"] = "closed"
    legacy_run = {key: run[key] for key in ("quiz_id", "title", "kind", "purpose", "closes_at")}
    from server.app.quiz.utils.training_completion import assignment_snapshot
    payload = {"run": legacy_run, "completion_register": [assignment_snapshot(item) for item in assignments()]}
    original = deepcopy(payload)
    repository.get_closure_audit.return_value = {"payload": payload}
    report = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert report["passing_threshold_percentage"] is None
    assert report["completion_register"][0]["outcome"] == "unknown"
    assert payload == original


@pytest.mark.parametrize("record,kind,state", [
    ({"assignment_id": "old-assignment", "recipient_email": "absent@example.com", "status": "assigned"}, "assigned", "assigned"),
    ({"session_id": "old-session", "participant_name": "Guest", "status": "submitted", "percentage": 75, "score": 3}, "shared_link", "completed"),
    ({"session_id": "old-session", "status": "abandoned"}, "shared_link", "incomplete"),
])
def test_legacy_row_discriminator_does_not_require_new_snapshot_fields(record, kind, state):
    original = deepcopy(record)
    row = completion_row(record, None)
    assert row["participant_type"] == kind
    assert row["status"] == state
    assert row["outcome"] == ("unknown" if state == "completed" else "not_completed")
    assert record == original


@pytest.mark.asyncio
async def test_closed_report_missing_snapshot_fails_without_live_fallback(caplog):
    service, repository, run = report_service()
    run["status"] = "closed"
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(str(run["_id"]), "owner-1")
    assert exc.value.status_code == 503
    repository.list_assignments_for_run.assert_not_awaited()
    assert "training_completion_report_unavailable" in caplog.text
    assert str(run["_id"]) in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("records", [None, [None], [{}], [{"assignment_id": "a", "status": "invalid"}]])
async def test_malformed_closed_evidence_returns_monitored_503_without_reconstruction(records, caplog):
    service, repository, run = report_service()
    run["status"] = "closed"
    repository.get_closure_audit.return_value = {"payload": {"run": {}, "completion_register": records}}
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(str(run["_id"]), "owner-1")
    assert exc.value.status_code == 503
    assert "training_completion_report_unavailable" in caplog.text
    repository.list_assignments_for_run.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("closed", [False, True])
async def test_oversized_details_remain_manageable_without_a_partial_register(monkeypatch, closed):
    import server.app.quiz.services.training_run_service as module

    monkeypatch.setattr(module, "MAX_COMPLETION_REPORT_ROWS", 1)
    service, repository, run = report_service()
    if closed:
        run["status"] = "closed"
        repository.get_closure_audit.return_value = {"payload": build_closure_payload(run, assignments(), [])}
    result = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert result["register_availability"] == "limit_exceeded"
    assert result["completion_register"] == []
    assert result["participant_count"] == 2
    assert result["completed_count"] == 1
    if closed:
        repository.get_closure_audit.assert_awaited_once_with(str(run["_id"]), report_limit=2)
        repository.get_closure_activity_summary.assert_awaited_once()
        repository.get_run_activity_summary.assert_not_awaited()
    else:
        repository.list_assignments_for_run.assert_awaited_once_with(str(run["_id"]), limit=2)


def test_snapshot_outcomes_remain_authoritative_when_a_threshold_is_changed_out_of_band():
    run = run_document()
    payload = build_closure_payload(run, assignments(), [])
    payload["run"]["passing_threshold_percentage"] = 99
    assert completion_row(payload["completion_register"][0], 99)["outcome"] == "passed"


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("state", ["future-state", None, {"unexpected": "state"}])
def test_closure_capture_preserves_unknown_states_without_blocking_finalization(shared, state, caplog):
    record = {"_id": ObjectId(), "status": state, "recipient_email": "private@example.com"}
    run = run_document()
    payload = build_closure_payload(run, [] if shared else [record], [record] if shared else [])
    frozen = payload["completion_register"][0]
    assert frozen["status"] == state
    assert frozen["outcome"] == "unknown"
    assert frozen["interpretation_error"] is True
    assert record["status"] == state
    assert "private@example.com" not in caplog.text
    assert "training_closure_uninterpretable_records" in caplog.text
    with pytest.raises(CompletionEvidenceError):
        completion_row(frozen, 80)


def test_closure_capture_keeps_malformed_timestamps_as_unknown_evidence():
    row = assignments()[0]
    row["completed_at"] = "legacy-invalid-time"
    frozen = build_closure_payload(run_document(), [row], [])["completion_register"][0]
    assert frozen["completed_at"] == "legacy-invalid-time"
    assert frozen["outcome"] == "unknown"
    assert frozen["interpretation_error"] is True


def test_shared_state_map_covers_the_live_session_contract_and_internal_states():
    from server.app.quiz.schemas.live_session_schemas import LiveQuizSessionState

    states = get_args(LiveQuizSessionState.model_fields["status"].annotation)
    assert set(states) <= SHARED_SESSION_STATES.keys()
    assert {"closing", "abandoned"} <= SHARED_SESSION_STATES.keys()


@pytest.mark.asyncio
async def test_closed_snapshot_nulls_respect_legacy_required_fields_and_optional_evidence():
    service, repository, run = report_service()
    run.update(status="closed", due_at=datetime.now(timezone.utc))
    payload = build_closure_payload(run, assignments(), [])
    payload["run"].update(access_mode=None, time_limit_minutes=None, due_at=None, passing_threshold_percentage=None)
    payload["run"].update(status="open", owner_user_id="another-owner", _id="replacement")
    repository.get_closure_audit.return_value = {"payload": payload}
    result = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert result["status"] == "closed"
    assert result["access_mode"] == "assigned_only"
    assert result["time_limit_minutes"] == 20
    assert result["due_at"] is None
    assert result["passing_threshold_percentage"] is None
    assert result["id"] == str(run["_id"])


def test_closure_builder_does_not_manufacture_null_metadata_for_absent_fields():
    run = run_document()
    run.pop("time_limit_minutes")
    payload = build_closure_payload(run, [], [])
    assert "time_limit_minutes" not in payload["run"]
    assert closed_run_metadata({"time_limit_minutes": 30}, payload["run"])["time_limit_minutes"] == 30


def test_closure_materializes_the_same_frozen_counters_as_its_register():
    run = run_document()
    payload = build_closure_payload(run, assignments(), [])
    assert payload["report_schema_version"] == 2
    assert payload["summary"] == completion_summary(
        completion_row(record, 80) for record in payload["completion_register"]
    )
    assert payload["summary"]["participant_count"] == 2
    assert payload["summary"]["completed_count"] == 1
    assert build_closure_payload(run, [], [])["summary"] == {
        "participant_count": 0, "assigned_count": 0, "started_count": 0,
        "completed_count": 0, "average_score": None,
    }


@pytest.mark.parametrize("outcome", ["unexpected", "", 0, [], "Passed"])
def test_invalid_stored_outcomes_raise_an_explicit_evidence_error(outcome):
    with pytest.raises(CompletionEvidenceError, match="Invalid stored completion outcome"):
        completion_row({"assignment_id": "a", "status": "completed", "outcome": outcome}, 80)


def test_worker_closure_persists_the_same_threshold_and_outcomes(monkeypatch):
    import server.app.quiz.tasks.training_run_tasks as tasks
    from server.tests.test_training_run_tasks import FakeClient, FakeDatabase

    run = run_document()
    run.update(
        passing_threshold_percentage=70, closure_in_progress=True, closure_mode="manual",
        closure_started_at=datetime.now(timezone.utc) - tasks.LOCK_STALE_AFTER,
    )
    rows = assignments()
    database = FakeDatabase(run, rows, [])
    client = FakeClient(database)
    monkeypatch.setattr(tasks, "MongoClient", lambda _uri: client)
    monkeypatch.setattr(tasks, "_utc_now", lambda: datetime.now(timezone.utc))
    assert tasks.close_expired_training_runs() == 1
    payload = database.audit_events.documents[0]["payload"]
    assert payload["run"]["passing_threshold_percentage"] == 70
    assert [row["outcome"] for row in payload["completion_register"]] == ["passed", "not_completed"]
    assert client.closed


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r", "\n", "  =", "\ufeff=", "＝"])
def test_csv_safely_encodes_untrusted_text_and_keeps_numeric_values(prefix):
    from server.app.quiz.utils.training_completion import completion_row, assignment_snapshot
    row = completion_row(assignment_snapshot(assignments()[0]), 80)
    row["recipient_name"] = prefix + 'formula,"name"'
    report = {
        "id": "run-1", "quiz_id": "quiz-1", "title": "Safety", "report_is_final": False,
        "passing_threshold_percentage": 80, "completion_register": [row],
    }
    parsed = list(csv.DictReader(io.StringIO(completion_report_csv(report, generated_at=datetime.now(timezone.utc)))))
    assert parsed[0]["assignee_name"].startswith("'")
    assert parsed[0]["score"] == "4"
    assert parsed[0]["percentage"] == "80"


@pytest.mark.parametrize("email", ["+recipient@example.com", "-recipient@example.com"])
def test_display_safe_csv_does_not_mutate_authoritative_email(email):
    record = {"assignment_id": "a", "recipient_email": email, "status": "assigned"}
    report = {
        "id": "run-1", "quiz_id": "quiz-1", "title": "Safety", "report_is_final": False,
        "passing_threshold_percentage": 80, "completion_register": [completion_row(record, 80)],
    }
    original = deepcopy(report)
    exported = list(csv.DictReader(io.StringIO(completion_report_csv(report, generated_at=datetime.now(timezone.utc)))))
    assert exported[0]["assignee_email"] == "'" + email
    assert report == original


@pytest.fixture
def report_app(monkeypatch):
    service, repository, run = report_service()
    run.update(organization_id="organization-1", created_by_user_id="owner-1")
    app = FastAPI()
    app.include_router(training_runs.router, prefix="/api/v1")
    user = SimpleNamespace(id="owner-1", is_verified=True, persona_category="corporate", persona_user_type="hr")
    app.dependency_overrides[get_current_user] = lambda: user
    app.state.membership_role = "owner"
    app.dependency_overrides[get_active_organization_context] = lambda: OrganizationContext(
        organization_id="organization-1", organization_kind="personal",
        membership_role=app.state.membership_role,
        principal=OrganizationPrincipal(user_id=user.id, session_id="session-1"), membership={},
    )
    app.dependency_overrides[training_runs.get_training_run_service] = lambda: service
    monkeypatch.setattr(limiter, "enabled", False)
    return app, user, repository, run


@pytest.mark.asyncio
@pytest.mark.parametrize("identity,status", [
    ("owner", 200), ("other", 200), ("employee", 200), ("unverified", 403),
    ("auditor", 200), ("learner", 403), ("author", 403),
    ("facilitator", 200), ("other_facilitator", 403),
])
async def test_report_route_uses_membership_policy_not_persona(report_app, identity, status):
    app, user, _, run = report_app
    if identity == "other":
        user.id = "other-manager"
    elif identity == "employee":
        user.persona_user_type = "employee"
    elif identity == "unverified":
        user.is_verified = False
    elif identity == "other_facilitator":
        user.id = "other-facilitator"
        app.state.membership_role = "facilitator"
    elif identity in {"auditor", "learner", "author", "facilitator"}:
        app.state.membership_role = identity
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/training-runs/{run['_id']}/completion-report.csv")
    assert response.status_code == status
    if status == 200:
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-type"].startswith("text/csv")
        assert "absent@example.com" in response.text


@pytest.mark.asyncio
async def test_missing_or_malformed_report_is_404(report_app):
    app, _, _, _ = report_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/training-runs/not-an-objectid/completion-report.csv")).status_code == 404


@pytest.mark.asyncio
async def test_csv_report_rejects_same_owners_run_in_another_organization(report_app):
    app, _, _, run = report_app
    run["organization_id"] = "another-organization"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/training-runs/{run['_id']}/completion-report.csv")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("closed", [False, True])
async def test_csv_route_refuses_oversized_reports_but_detail_returns_summary(report_app, monkeypatch, closed):
    import server.app.quiz.services.training_run_service as module

    monkeypatch.setattr(module, "MAX_COMPLETION_REPORT_ROWS", 1)
    app, _, repository, run = report_app
    if closed:
        run["status"] = "closed"
        repository.get_closure_audit.return_value = {"payload": build_closure_payload(run, assignments(), [])}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        detail = await client.get(f"/api/v1/training-runs/{run['_id']}")
        csv_response = await client.get(f"/api/v1/training-runs/{run['_id']}/completion-report.csv")
    assert detail.status_code == 200
    assert detail.json()["register_availability"] == "limit_exceeded"
    assert detail.json()["participant_count"] == 2
    assert csv_response.status_code == 413
    assert "no partial CSV" in csv_response.json()["detail"]


@pytest.mark.asyncio
async def test_register_at_exact_ceiling_is_available():
    rows = [assignments()[0]] * MAX_COMPLETION_REPORT_ROWS
    service, _, run = report_service(rows=rows)
    result = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert result["register_availability"] == "available"
    assert len(result["completion_register"]) == MAX_COMPLETION_REPORT_ROWS


@pytest.mark.asyncio
async def test_submitting_is_a_started_assignment_not_a_report_failure():
    rows = assignments()
    rows[0]["status"] = "submitting"
    service, _, run = report_service(rows=rows)
    result = await service.get_owner_run(str(run["_id"]), "owner-1")
    assert result["completion_register"][0]["status"] == "in_progress"
    assert result["started_count"] == 1
    assert result["completed_count"] == 0
    assert rows[0]["status"] == "submitting"


@pytest.mark.parametrize("score,expected", [(2, 2), (2.0, 2), (2.5, None), (True, None), (-1, None), (float("nan"), None), (float("inf"), None)])
def test_raw_score_contract_is_consistent_for_rows_and_summaries(score, expected):
    row = completion_row({"assignment_id": "a", "status": "completed", "latest_score": score}, 80)
    assert row["latest_score"] == expected
    assert completion_summary([row])["average_score"] == expected


@pytest.mark.asyncio
async def test_unexpected_repository_errors_are_not_mislabeled_as_corrupt_evidence():
    service, repository, run = report_service()
    repository.list_assignments_for_run.side_effect = TypeError("Unexpected implementation defect")
    with pytest.raises(TypeError, match="Unexpected implementation defect"):
        await service.get_owner_run(str(run["_id"]), "owner-1")


@pytest.mark.asyncio
async def test_validation_diagnostics_keep_the_stack_without_participant_values(caplog):
    service, repository, run = report_service()
    run["status"] = "closed"
    repository.get_closure_audit.return_value = {"payload": {
        "run": {}, "completion_register": [{
            "assignment_id": "a", "status": "assigned", "recipient_email": "private-invalid-email",
        }],
    }}
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(str(run["_id"]), "owner-1")
    assert exc.value.status_code == 503
    assert "private-invalid-email" not in caplog.text
    assert "Traceback" in caplog.text
