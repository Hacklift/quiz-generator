from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from pymongo import MongoClient

import pytest
from bson import ObjectId
from fastapi import HTTPException, FastAPI
from httpx import AsyncClient, ASGITransport

from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.services.training_run_service import TrainingRunService
from server.app.quiz.routes import training_runs
from server.app.core.dependencies import get_current_user
from server.app.quiz.utils.training_completion import build_closure_payload, MAX_COMPLETION_REPORT_ROWS, completion_row, completion_summary
from server.tests.test_training_completion_reports import run_document


def repository_for(database):
    return TrainingRunRepository(
        database.quizzes_v2, database.training_runs, database.training_assignments,
        database.training_audit_events, database.live_quiz_sessions,
    )


@pytest.mark.asyncio
async def test_real_mongo_report_is_complete_owner_scoped_and_frozen_after_closure(test_db):
    run = run_document()
    run_id = str(run["_id"])
    run["access_mode"] = "public"
    await test_db.training_runs.insert_one(run)
    assignment = {
        "_id": ObjectId(), "training_run_id": run_id,
        "recipient_email": "absent@example.com", "status": "assigned",
    }
    await test_db.training_assignments.insert_one(assignment)
    now = datetime.now(timezone.utc)
    await test_db.live_quiz_sessions.insert_many([
        {
            "_id": ObjectId(), "training_run_id": run_id,
            "participant_name": f"Participant {index}", "status": "submitted",
            "score": 4, "percentage": 80, "submitted_at": now,
            "created_at": now + timedelta(milliseconds=index),
        }
        for index in range(2001)
    ])
    # A different run must never leak into this report.
    await test_db.live_quiz_sessions.insert_one({
        "training_run_id": "another-run", "participant_email": "private@example.com",
        "status": "submitted", "percentage": 100,
    })
    repository = repository_for(test_db)
    service = TrainingRunService(repository, SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(run_id, "another-owner")
    assert exc.value.status_code == 404
    provisional = await service.get_owner_run(run_id, "owner-1")
    assert len(provisional["completion_register"]) == 2002
    assert provisional["completed_count"] == 2001
    assert provisional["completion_register"][1]["completed_at"].tzinfo == timezone.utc
    assert "private@example.com" not in str(provisional)

    await service.close_owner_run(run_id, "owner-1")
    audit = await repository.get_closure_audit(run_id)
    assert audit["payload"]["run"]["passing_threshold_percentage"] == 80
    assert len(audit["payload"]["completion_register"]) == 2002
    assert audit["payload"]["completion_register"][1]["outcome"] == "passed"
    await test_db.live_quiz_sessions.update_many(
        {"training_run_id": run_id}, {"$set": {"percentage": 0, "score": 0}}
    )
    await test_db.training_assignments.delete_many({"training_run_id": run_id})
    await test_db.training_runs.update_one({"_id": run["_id"]}, {"$set": {"passing_threshold_percentage": 100}})
    final = await service.get_owner_run(run_id, "owner-1")
    assert final["report_is_final"] is True
    assert final["passing_threshold_percentage"] == 80
    assert final["report_finalized_at"].tzinfo == timezone.utc
    assert len(final["completion_register"]) == 2002
    assert final["completion_register"][1]["outcome"] == "passed"
    listed = await service.list_owner_runs("owner-1")
    assert listed[0]["completed_count"] == final["completed_count"]
    assert listed[0]["assigned_count"] == final["assigned_count"]
    assert listed[0]["average_score"] == final["average_score"]
    assert listed[0]["passing_threshold_percentage"] == 80
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run("not-an-objectid", "owner-1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_real_mongo_closure_audit_insert_does_not_overwrite_existing_evidence(test_db):
    repository = repository_for(test_db)
    await test_db.training_audit_events.create_index(
        [("training_run_id", 1), ("event_type", 1)], unique=True,
    )
    run = run_document()
    event = {
        "training_run_id": str(run["_id"]), "event_type": "run_closed",
        "occurred_at": datetime.now(timezone.utc),
        "payload": build_closure_payload(run, [], []),
    }
    await repository.create_audit_event(event)
    changed = {**event, "payload": {"run": {"passing_threshold_percentage": 0}}}
    changed.pop("_id", None)
    await repository.create_audit_event(changed)
    audit = await repository.get_closure_audit(str(run["_id"]))
    assert audit["payload"]["run"]["passing_threshold_percentage"] == 80


@pytest.mark.asyncio
async def test_interactive_reads_are_bounded_but_closure_evidence_is_not(test_db, monkeypatch):
    import server.app.quiz.services.training_run_service as module

    monkeypatch.setattr(module, "MAX_COMPLETION_REPORT_ROWS", 3)
    run = run_document()
    await test_db.training_runs.insert_one(run)
    run_id = str(run["_id"])
    await test_db.live_quiz_sessions.insert_many([
        {
            "training_run_id": run_id, "status": "submitted", "participant_name": f"Person {i}",
            "created_at": run["created_at"], "percentage": 80, "score": 4,
            "quiz_snapshot": {"questions": ["not needed in a report"]},
        } for i in range(6)
    ])
    repository = repository_for(test_db)
    limited = await repository.list_sessions_for_run(run_id, limit=4, shared_only=True)
    assert len(limited) == 4
    assert all("quiz_snapshot" not in row for row in limited)
    service = TrainingRunService(repository, SimpleNamespace())
    detail = await service.get_owner_run(run_id, "owner-1")
    assert detail["register_availability"] == "limit_exceeded"
    assert detail["participant_count"] == 6
    assert detail["completion_register"] == []
    # The list remains usable without loading/truncating participant records.
    listed = await service.list_owner_runs("owner-1")
    assert listed[0]["completed_count"] == 6
    await service.close_owner_run(run_id, "owner-1")
    full = await repository.get_closure_audit(run_id)
    assert len(full["payload"]["completion_register"]) == 6
    limited_audit = await repository.get_closure_audit(run_id, report_limit=4)
    assert len(limited_audit["payload"]["completion_register"]) == 4
    assert "quiz_snapshot" not in limited_audit["payload"]["run"]
    assert limited_audit["payload"]["run"]["passing_threshold_percentage"] == 80
    # Large closed summaries must use the retained register, not live rows.
    await test_db.live_quiz_sessions.delete_many({"training_run_id": run_id})
    final = await service.get_owner_run(run_id, "owner-1")
    assert final["register_availability"] == "limit_exceeded"
    assert final["participant_count"] == final["completed_count"] == 6
    assert final["average_score"] == 4


@pytest.mark.asyncio
async def test_database_activity_summary_matches_existing_count_and_score_semantics(test_db):
    run_id = "run-1"
    await test_db.training_assignments.insert_many([
        {"training_run_id": run_id, "status": "completed", "latest_score": 2},
        {"training_run_id": run_id, "status": "assigned"},
        {"training_run_id": run_id, "status": "in_progress", "latest_score": 100},
        {"training_run_id": run_id, "status": "completed", "latest_score": None},
        {"training_run_id": "other-run", "status": "completed", "latest_score": 100},
    ])
    await test_db.live_quiz_sessions.insert_many([
        {"training_run_id": run_id, "status": "submitted", "score": 4},
        {"training_run_id": run_id, "status": "active", "score": 100},
        {"training_run_id": run_id, "status": "submitted", "score": 100, "training_assignment_id": "assigned-session"},
        {"training_run_id": "other-run", "status": "submitted", "score": 100},
    ])
    repository = repository_for(test_db)
    assert await repository.get_run_activity_summary(run_id) == {
        "participant_count": 6, "assigned_count": 4, "started_count": 5, "completed_count": 3, "average_score": 3,
    }
    assert await repository.get_run_activity_summary("missing-run") == {
        "participant_count": 0, "assigned_count": 0, "started_count": 0, "completed_count": 0, "average_score": None,
    }


@pytest.mark.asyncio
async def test_run_list_uses_two_batched_aggregations_and_only_authorized_run_ids(test_db):
    runs = [run_document() for _ in range(4)]
    other = run_document()
    other["owner_user_id"] = "another-owner"
    await test_db.training_runs.insert_many([*runs, other])
    await test_db.training_assignments.insert_many([
        {"training_run_id": str(run["_id"]), "status": "completed", "latest_score": index}
        for index, run in enumerate([*runs, other])
    ])
    repository = repository_for(test_db)
    assignment_aggregate = Mock(wraps=test_db.training_assignments.aggregate)
    session_aggregate = Mock(wraps=test_db.live_quiz_sessions.aggregate)
    repository.assignments_collection = SimpleNamespace(aggregate=assignment_aggregate)
    repository.sessions_collection = SimpleNamespace(aggregate=session_aggregate)
    result = await TrainingRunService(repository, SimpleNamespace()).list_owner_runs("owner-1")
    assert len(result) == 4
    assert {item["average_score"] for item in result} == {0, 1, 2, 3}
    assignment_aggregate.assert_called_once()
    session_aggregate.assert_called_once()
    for aggregate in (assignment_aggregate, session_aggregate):
        selected_ids = aggregate.call_args.args[0][0]["$match"]["training_run_id"]["$in"]
        assert set(selected_ids) == {str(run["_id"]) for run in runs}
    assignment_aggregate.reset_mock()
    session_aggregate.reset_mock()
    assert await repository.get_run_activity_summaries([]) == {}
    assignment_aggregate.assert_not_called()
    session_aggregate.assert_not_called()


@pytest.mark.asyncio
async def test_database_and_python_summary_rules_match_submitting_and_integer_scores(test_db):
    records = [
        {"assignment_id": str(i), "status": status, "latest_score": score}
        for i, (status, score) in enumerate([
            ("submitting", 4), ("in_progress", None), ("assigned", None),
            ("completed", 2), ("completed", 4.0), ("completed", 2.5),
            ("completed", True), ("completed", float("nan")), ("completed", float("inf")),
        ])
    ]
    await test_db.training_assignments.insert_many([
        {"training_run_id": "run-1", "status": row["status"], "latest_score": row["latest_score"]}
        for row in records
    ])
    expected = completion_summary([completion_row(row, 80) for row in records])
    assert await repository_for(test_db).get_run_activity_summary("run-1") == expected
    await test_db.training_audit_events.insert_one({
        "training_run_id": "run-1", "event_type": "run_closed",
        "payload": {"run": {}, "completion_register": records},
    })
    assert await repository_for(test_db).get_closure_activity_summary("run-1") == expected


@pytest.mark.asyncio
async def test_real_default_slice_boundary_keeps_large_closed_run_accessible(test_db):
    run = run_document()
    run["status"] = "closed"
    run_id = str(run["_id"])
    await test_db.training_runs.insert_one(run)
    records = [{
        "session_id": str(i), "status": "submitted", "score": 1, "percentage": 100,
    } for i in range(MAX_COMPLETION_REPORT_ROWS + 1)]
    await test_db.training_audit_events.insert_one({
        "training_run_id": run_id, "event_type": "run_closed", "occurred_at": run["created_at"],
        "payload": {"run": {"passing_threshold_percentage": 80}, "completion_register": records},
    })
    repository = repository_for(test_db)
    limited = await repository.get_closure_audit(run_id, report_limit=MAX_COMPLETION_REPORT_ROWS + 1)
    assert len(limited["payload"]["completion_register"]) == MAX_COMPLETION_REPORT_ROWS + 1
    result = await TrainingRunService(repository, SimpleNamespace()).get_owner_run(run_id, "owner-1")
    assert result["register_availability"] == "limit_exceeded"
    assert result["participant_count"] == result["completed_count"] == MAX_COMPLETION_REPORT_ROWS + 1
    assert result["report_is_final"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("shared", [False, True])
async def test_manual_close_completes_with_unknown_record_states_and_reports_stay_strict(test_db, shared):
    run = run_document()
    run.update(kind="business", purpose="custom", access_mode="public", access_code="TEST999")
    await test_db.training_runs.insert_one(run)
    run_id = str(run["_id"])
    collection = test_db.live_quiz_sessions if shared else test_db.training_assignments
    source = {
        "training_run_id": run_id, "status": "new-unsupported-state", "recipient_email": "learner@example.com",
    }
    await collection.insert_one(source)
    service = TrainingRunService(repository_for(test_db), SimpleNamespace())
    await service.close_owner_run(run_id, "owner-1")
    stored = await test_db.training_runs.find_one({"_id": run["_id"]})
    assert stored["status"] == "closed"
    audit = await test_db.training_audit_events.find_one({"training_run_id": run_id})
    assert audit["payload"]["completion_register"][0]["status"] == "new-unsupported-state"
    assert audit["payload"]["completion_register"][0]["outcome"] == "unknown"
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(run_id, "owner-1")
    assert exc.value.status_code == 503
    listed = await service.list_owner_runs("owner-1")
    assert listed[0]["summary_availability"] == "unavailable"
    with pytest.raises(HTTPException) as exc:
        await service._get_public_startable_run("TEST999")
    assert exc.value.status_code == 410


@pytest.mark.asyncio
async def test_scheduled_closure_captures_unknown_records_without_repeated_failure(test_db, mongo_container, monkeypatch):
    import server.app.quiz.tasks.training_run_tasks as tasks

    run = run_document()
    run["closes_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    await test_db.training_runs.insert_one(run)
    run_id = str(run["_id"])
    await test_db.live_quiz_sessions.insert_one({"training_run_id": run_id, "status": "legacy-unknown-state"})
    await test_db.training_assignments.insert_one({"training_run_id": run_id, "status": None})
    monkeypatch.setenv("DB_NAME", test_db.name)
    monkeypatch.setattr(tasks, "MongoClient", lambda _uri: MongoClient(mongo_container.get_connection_url()))
    assert tasks.close_expired_training_runs() == 1
    assert tasks.close_expired_training_runs() == 0
    audit = await test_db.training_audit_events.find_one({"training_run_id": run_id})
    assert [row["outcome"] for row in audit["payload"]["completion_register"]] == ["unknown", "unknown"]


@pytest.mark.asyncio
async def test_worker_manual_recovery_terminalizes_submitting_assignments(test_db, mongo_container, monkeypatch):
    import server.app.quiz.tasks.training_run_tasks as tasks

    run = run_document()
    run.update(
        closure_in_progress=True, closure_mode="manual",
        closure_started_at=datetime.now(timezone.utc) - tasks.LOCK_STALE_AFTER,
    )
    await test_db.training_runs.insert_one(run)
    run_id = str(run["_id"])
    await test_db.training_assignments.insert_one({
        "training_run_id": run_id, "recipient_email": "learner@example.com", "status": "submitting",
    })
    monkeypatch.setenv("DB_NAME", test_db.name)
    monkeypatch.setattr(tasks, "MongoClient", lambda _uri: MongoClient(mongo_container.get_connection_url()))
    assert tasks.close_expired_training_runs() == 1
    row = await test_db.training_assignments.find_one({"training_run_id": run_id})
    assert row["status"] == "incomplete"


@pytest.mark.asyncio
async def test_closed_list_batches_snapshots_including_empty_and_missing_evidence(test_db):
    closed = [run_document() for _ in range(3)]
    for run in closed:
        run["status"] = "closed"
    opened = run_document()
    await test_db.training_runs.insert_many([*closed, opened])
    records = [{"assignment_id": "a", "status": "completed", "latest_score": 3}]
    await test_db.training_audit_events.insert_many([
        {"training_run_id": str(closed[0]["_id"]), "event_type": "run_closed", "payload": {
            "run": {"title": "Frozen title", "access_mode": None, "time_limit_minutes": None},
            "completion_register": records,
        }},
        {"training_run_id": str(closed[1]["_id"]), "event_type": "run_closed", "payload": {
            "run": {}, "completion_register": [],
        }},
    ])
    # Live rows for closed runs must never influence their final counters.
    await test_db.training_assignments.insert_many([
        {"training_run_id": str(run["_id"]), "status": "completed", "latest_score": 999}
        for run in closed
    ])
    repository = repository_for(test_db)
    assignment_aggregate = Mock(wraps=test_db.training_assignments.aggregate)
    session_aggregate = Mock(wraps=test_db.live_quiz_sessions.aggregate)
    audit_aggregate = Mock(wraps=test_db.training_audit_events.aggregate)
    audit_find = Mock(wraps=test_db.training_audit_events.find)
    repository.assignments_collection = SimpleNamespace(aggregate=assignment_aggregate)
    repository.sessions_collection = SimpleNamespace(aggregate=session_aggregate)
    repository.audit_events_collection = SimpleNamespace(
        aggregate=audit_aggregate, find=audit_find,
    )
    listed = await TrainingRunService(repository, SimpleNamespace()).list_owner_runs("owner-1")
    by_id = {item["id"]: item for item in listed}
    assert by_id[str(closed[0]["_id"])]["title"] == "Frozen title"
    assert by_id[str(closed[0]["_id"])]["average_score"] == 3
    assert by_id[str(closed[1]["_id"])]["participant_count"] == 0
    assert by_id[str(closed[1]["_id"])]["summary_availability"] == "available"
    assert by_id[str(closed[2]["_id"])]["summary_availability"] == "unavailable"
    for aggregate in (assignment_aggregate, session_aggregate):
        aggregate.assert_called_once()
        assert aggregate.call_args.args[0][0]["$match"]["training_run_id"]["$in"] == [str(opened["_id"])]
    audit_aggregate.assert_called_once()
    # The bounded lookup sees all selected closed runs; aggregation is only
    # needed for the two existing legacy payloads, not the absent audit.
    audit_find.assert_called_once()
    assert set(audit_find.call_args.args[0]["training_run_id"]["$in"]) == {str(run["_id"]) for run in closed}
    assert set(audit_aggregate.call_args.args[0][0]["$match"]["training_run_id"]["$in"]) == {str(run["_id"]) for run in closed[:2]}


@pytest.mark.asyncio
async def test_materialized_summaries_do_not_read_or_aggregate_current_registers(test_db):
    runs = [run_document() for _ in range(2)]
    for run in runs:
        run["status"] = "closed"
    payloads = [build_closure_payload(run, [], []) for run in runs]
    payloads[1].pop("summary")
    payloads[1]["report_schema_version"] = 1
    await test_db.training_audit_events.insert_many([
        {"training_run_id": str(run["_id"]), "event_type": "run_closed", "payload": payload}
        for run, payload in zip(runs, payloads)
    ])
    find = Mock(wraps=test_db.training_audit_events.find)
    aggregate = Mock(wraps=test_db.training_audit_events.aggregate)
    repository = repository_for(test_db)
    repository.audit_events_collection = SimpleNamespace(find=find, aggregate=aggregate)
    ids = [str(run["_id"]) for run in runs]
    result = await repository.get_closure_report_summaries(ids)
    assert set(result) == set(ids)
    find.assert_called_once()
    projection = find.call_args.args[1]
    assert projection["payload.summary"] == 1
    assert "payload.completion_register" not in projection
    assert "payload.run.quiz_snapshot" not in projection
    aggregate.assert_called_once()
    assert aggregate.call_args.args[0][0]["$match"]["training_run_id"]["$in"] == [ids[1]]
    aggregate.reset_mock()
    await repository.get_closure_report_summaries([ids[0]])
    aggregate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("summary", [None, {}, {"participant_count": True}, {
    "participant_count": 1, "assigned_count": 1, "started_count": 0,
    "completed_count": 2, "average_score": 1,
}])
async def test_malformed_materialized_summaries_are_not_recomputed_as_legacy(test_db, summary):
    run = run_document()
    payload = build_closure_payload(run, [], [])
    payload["summary"] = summary
    await test_db.training_audit_events.insert_one({
        "training_run_id": str(run["_id"]), "event_type": "run_closed", "payload": payload,
    })
    aggregate = Mock(wraps=test_db.training_audit_events.aggregate)
    repository = repository_for(test_db)
    repository.audit_events_collection = SimpleNamespace(find=test_db.training_audit_events.find, aggregate=aggregate)
    assert await repository.get_closure_report_summaries([str(run["_id"])]) == {}
    aggregate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True])
async def test_mixed_bad_evidence_only_marks_its_own_run_unavailable_on_the_list_endpoint(test_db, legacy):
    good, bad = run_document(), run_document()
    good["status"] = bad["status"] = "closed"
    await test_db.training_runs.insert_many([good, bad])
    valid = {"_id": ObjectId(), "recipient_email": "learner@example.com", "status": "completed", "latest_score": 4}
    invalid = {"_id": ObjectId(), "recipient_email": "other@example.com", "status": "future-state"}
    good_payload = build_closure_payload(good, [valid], [])
    bad_payload = build_closure_payload(bad, [valid, invalid], [])
    assert bad_payload["summary"] is None
    assert len(bad_payload["completion_register"]) == 2
    assert bad_payload["completion_register"][1]["interpretation_error"] is True
    if legacy:
        for payload in (good_payload, bad_payload):
            payload.pop("summary")
            payload["report_schema_version"] = 1
    await test_db.training_audit_events.insert_many([
        {"training_run_id": str(run["_id"]), "event_type": "run_closed", "payload": payload}
        for run, payload in ((good, good_payload), (bad, bad_payload))
    ])
    app = FastAPI()
    app.include_router(training_runs.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="owner-1", is_verified=True, persona_category="corporate", persona_user_type="hr",
    )
    service = TrainingRunService(repository_for(test_db), SimpleNamespace())
    app.dependency_overrides[training_runs.get_training_run_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/training-runs")
    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()}
    assert len(by_id) == 2
    assert by_id[str(good["_id"])]["summary_availability"] == "available"
    assert by_id[str(good["_id"])]["completed_count"] == 1
    assert by_id[str(bad["_id"])]["summary_availability"] == "unavailable"


@pytest.mark.asyncio
async def test_shared_state_mapping_is_identical_for_live_frozen_and_legacy_summaries(test_db):
    from server.app.quiz.utils.training_completion import SHARED_SESSION_STATES

    run = run_document()
    run_id = str(run["_id"])
    sessions = [{
        "_id": ObjectId(), "training_run_id": run_id, "status": state,
        "score": 3, "percentage": 75,
    } for state in SHARED_SESSION_STATES]
    await test_db.live_quiz_sessions.insert_many(sessions)
    payload = build_closure_payload(run, [], sessions)
    expected = payload["summary"]
    repository = repository_for(test_db)
    assert await repository.get_run_activity_summary(run_id) == expected
    event = {"training_run_id": run_id, "event_type": "run_closed", "payload": payload}
    await test_db.training_audit_events.insert_one(event)
    assert await repository.get_closure_activity_summary(run_id) == expected
    await test_db.training_audit_events.update_one({"_id": event["_id"]}, {
        "$unset": {"payload.summary": ""}, "$set": {"payload.report_schema_version": 1},
    })
    assert await repository.get_closure_activity_summary(run_id) == expected
    expression = repository._shared_session_state("$status")
    assert {branch["case"]["$eq"][1]: branch["then"] for branch in expression["$switch"]["branches"]} == SHARED_SESSION_STATES
