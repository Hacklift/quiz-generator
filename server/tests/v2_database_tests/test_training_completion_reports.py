from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.services.training_run_service import TrainingRunService
from server.app.quiz.utils.training_completion import build_closure_payload
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
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(run_id, "owner-1")
    assert exc.value.status_code == 413
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
    with pytest.raises(HTTPException) as exc:
        await service.get_owner_run(run_id, "owner-1")
    assert exc.value.status_code == 413


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
        "assigned_count": 4, "started_count": 5, "completed_count": 3, "average_score": 3,
    }
    assert await repository.get_run_activity_summary("missing-run") == {
        "assigned_count": 0, "started_count": 0, "completed_count": 0, "average_score": None,
    }
