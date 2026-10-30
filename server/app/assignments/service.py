"""Assignment orchestration; training owns delivery, retries and finalization."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from types import SimpleNamespace
from typing import Protocol

from fastapi import HTTPException
from pydantic import ValidationError

from server.app.assignments.models import AssignmentProgressStatistics, RecipientProgress
from server.app.assignments.repository import ASSIGNMENT_SUMMARY_FIELDS, page
from server.app.assignments.statistics import has_completed
from server.app.organizations.policy import OrganizationAction, OrganizationPolicy

logger = logging.getLogger(__name__)

def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc)


class CohortDeliveryGateway(Protocol):
    async def get_cohort(self, organization_id: str, cohort_id: str) -> dict | None: ...
    async def recipient_ids(self, context, cohort_id: str) -> list[str]: ...
    async def can(self, context, cohort_id: str, capability: str) -> bool: ...
    async def accessible_ids(self, context, capability: str) -> list[str]: ...


class AssignmentService:
    def __init__(self, repository, training_service, cohorts: CohortDeliveryGateway):
        self.repository = repository
        self.training = training_service
        self.cohorts = cohorts
        self.policy = OrganizationPolicy()

    async def _run(self, context, assignment_id):
        run = await self.repository.run(context.organization_id, assignment_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return run

    async def _can(self, context, run, capability):
        cohort_id = run.get("cohort_id")
        if cohort_id:
            return await self.cohorts.can(context, cohort_id, capability)
        action = {
            "assign": OrganizationAction.ASSIGNMENT_MANAGE,
            "report": OrganizationAction.COHORT_REPORT,
            "attempt": OrganizationAction.MEMBER_ATTEMPT_READ,
        }[capability]
        return self.policy.can(context.principal, action, run, context)

    async def _require(self, context, run, capability):
        if not await self._can(context, run, capability):
            raise HTTPException(status_code=403, detail="Assignment permission denied")

    @staticmethod
    def fingerprint(payload, organization_id):
        # No resolved roster or implicit 'now': retries describe the original
        # intent and resume its frozen recipients, even after roster changes.
        data = payload.model_dump(mode="json")
        data["organization_id"] = organization_id
        data["passing_threshold_percentage"] = float(data["passing_threshold_percentage"])
        return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    async def create(self, context, payload, idempotency_key):
        org, actor = context.organization_id, context.principal.user_id
        fingerprint = self.fingerprint(payload, org)
        existing = await self.training.repository.get_run_by_idempotency_key(actor, idempotency_key, organization_id=org)
        if existing:
            if existing.get("delivery_kind") != "quiz" or existing.get("request_fingerprint") != fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency key was already used for a different assignment")
            await self._require(context, existing, "assign")
            await self.training._resume_or_return_run(existing, now())
            return await self.detail(context, str(existing["_id"]))

        available_from = payload.available_from or now()
        if utc(payload.closes_at) <= max(now(), available_from) + timedelta(minutes=payload.time_limit_minutes):
            raise HTTPException(status_code=400, detail="Availability must allow one full attempt")
        if payload.due_at and payload.due_at < available_from:
            raise HTTPException(status_code=400, detail="Due time must not precede availability")
        quiz = await self.training.repository.get_quiz_for_organization(payload.quiz_id, org)
        library_source = False
        if not quiz:
            quiz = await self.repository.library_quiz(payload.quiz_id)
            library_source = quiz is not None
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if not quiz.get("questions"):
            raise HTTPException(status_code=400, detail="Quiz has no questions")
        if not library_source and not self.policy.can(context.principal, OrganizationAction.CONTENT_READ, quiz, context):
            raise HTTPException(status_code=403, detail="Quiz permission denied")
        if payload.cohort_id:
            cohort = await self.cohorts.get_cohort(org, payload.cohort_id)
            if not cohort:
                raise HTTPException(status_code=404, detail="Cohort not found")
            if cohort.get("status") != "active":
                raise HTTPException(status_code=409, detail="Cohort is archived")
            await self._require(context, {**quiz, "cohort_id": payload.cohort_id}, "assign")
            ids = await self.cohorts.recipient_ids(context, payload.cohort_id)
        else:
            target = {"organization_id": org, "created_by_user_id": actor, "owner_user_id": actor}
            if not self.policy.can(context.principal, OrganizationAction.ASSIGNMENT_CREATE, target, context):
                raise HTTPException(status_code=403, detail="Assignment permission denied")
            ids = payload.recipient_user_ids
        recipients = await self.repository.active_recipients(org, ids)
        if len({recipient["email"] for recipient in recipients}) != len(recipients):
            raise HTTPException(status_code=409, detail="Recipient delivery identities require reconciliation")
        revision = await self.repository.revisions.snapshot(org, quiz, actor)
        snapshot = {
            "request_fingerprint": fingerprint, "delivery_kind": "quiz",
            "cohort_id": payload.cohort_id, "available_from": available_from,
            "quiz_revision_id": str(revision["_id"]), "quiz_snapshot": revision["snapshot"],
            "recipient_user_ids": {recipient["email"]: recipient["user_id"] for recipient in recipients},
            "recipient_names": {recipient["email"]: recipient["name"] for recipient in recipients},
            "recipient_snapshot": recipients,
            "delegation_snapshot": {"actor_user_id": actor, "cohort_id": payload.cohort_id, "can_assign": True},
        }
        training_payload = SimpleNamespace(
            **payload.model_dump(exclude={"cohort_id", "recipient_user_ids", "available_from"}),
            kind="quiz", purpose="custom", access_mode="assigned_only",
            recipient_emails=[recipient["email"] for recipient in recipients],
        )
        result = await self.training.create_run(training_payload, actor, idempotency_key,
            organization_id=org, authorized_quiz=quiz, delivery_snapshot=snapshot)
        return await self.detail(context, result["id"])

    @staticmethod
    def _summary(run):
        return {"id": str(run["_id"]), **{key: run.get(key) for key in ASSIGNMENT_SUMMARY_FIELDS}}

    async def _summaries(self, context, runs):
        stats = await self.repository.summaries(context.organization_id, runs)
        summaries = []
        for run in runs:
            try:
                validated = AssignmentProgressStatistics.model_validate(stats.get(str(run["_id"]))).model_dump()
            except ValidationError:
                validated = None
            summaries.append({**self._summary(run), **(validated or {}),
                "summary_availability": "available" if validated is not None else "unavailable"})
        return summaries

    async def list(self, context, *, cursor=None, limit=25, cohort_id=None):
        query = {"organization_id": context.organization_id, "delivery_kind": "quiz", "status": {"$in": ["open", "closed"]}}
        resource = {"organization_id": context.organization_id}
        global_assign = self.policy.can(context.principal, OrganizationAction.ASSIGNMENT_MANAGE, resource, context)
        global_report = self.policy.can(context.principal, OrganizationAction.COHORT_REPORT, resource, context)
        assignable, reportable = set(), set()
        if cohort_id:
            cohort = await self.cohorts.get_cohort(context.organization_id, cohort_id)
            if not cohort:
                raise HTTPException(status_code=404, detail="Cohort not found")
            await self._require(context, {**query, "cohort_id": cohort_id}, "report")
            query["cohort_id"] = cohort_id
            reportable.add(cohort_id)
        elif not (global_assign or global_report):
            assignable = set(await self.cohorts.accessible_ids(context, "assign"))
            reportable = set(await self.cohorts.accessible_ids(context, "report"))
            if len(assignable | reportable) > 1000:
                raise HTTPException(status_code=413, detail="Select a cohort to browse assignments across more than 1000 delegations")
            query["$or"] = [
                {"cohort_id": {"$in": list(assignable | reportable)}},
                {"cohort_id": None, "created_by_user_id": context.principal.user_id},
            ]
        runs, next_cursor = await page(self.training.repository.runs_collection, query, cursor=cursor, limit=limit)
        report_runs = [run for run in runs if global_report or run.get("cohort_id") in reportable
            or (not run.get("cohort_id") and self.policy.can(
                context.principal, OrganizationAction.COHORT_REPORT, run, context))]
        summaries = {item["id"]: item for item in await self._summaries(context, report_runs)}
        items = [summaries.get(str(run["_id"]), self._summary(run)) for run in runs]
        return {"items": items, "next_cursor": next_cursor}

    async def mine(self, context, *, cursor=None, limit=25):
        recipients, next_cursor = await self.repository.my_assignments(
            context.organization_id, context.principal.user_id, cursor=cursor, limit=limit)
        frozen = await self.repository.frozen_user_rows(context.organization_id,
            [row["training_run_id"] for row in recipients if row["_run"]["status"] == "closed"], context.principal.user_id)
        items = []
        for row in recipients:
            run = row["_run"]
            evidence = frozen.get(row["training_run_id"]) if run["status"] == "closed" else row
            if evidence is None:
                raise HTTPException(status_code=503, detail="Final completion record is unavailable")
            items.append({**self._summary(run), **self._recipient(evidence, run)})
        return {"items": items, "next_cursor": next_cursor}

    @staticmethod
    def _recipient(row, run):
        try:
            if not isinstance(row, dict) or row.get("interpretation_error"):
                raise ValueError("Invalid retained recipient")
            return RecipientProgress.model_validate(AssignmentService._recipient_payload(row, run)).model_dump()
        except (ValidationError, KeyError, TypeError, ValueError, AttributeError):
            logger.exception("Invalid assignment completion evidence for run %s", run.get("_id"))
            raise HTTPException(status_code=503, detail="Completion record is unavailable") from None

    @staticmethod
    def _recipient_payload(row, run):
        current = now()
        latest_start = utc(run["closes_at"]) - timedelta(minutes=run["time_limit_minutes"])
        available = utc(run.get("available_from") or run["created_at"]) <= current
        attempts = row.get("attempts_used", 0)
        maximum = row.get("max_attempts")
        return {
            "recipient_id": str(row.get("_id") or row.get("assignment_id")),
            "user_id": row.get("recipient_user_id"), "recipient_name": row.get("recipient_name"),
            "recipient_status": row["status"], "attempts_used": attempts, "max_attempts": maximum,
            "latest_score": row.get("latest_score"), "latest_percentage": row.get("latest_percentage"),
            "completed_at": row.get("completed_at"), "has_completed": has_completed(row),
            "active_session_id": row.get("active_session_id"),
            "can_resume": bool(available and run["status"] == "open" and not run.get("closure_in_progress")
                and current < utc(run["closes_at"]) and row["status"] == "in_progress" and row.get("active_session_id")),
            "can_start": bool(available and run["status"] == "open" and not run.get("closure_in_progress")
                and current <= latest_start and row["status"] in {"assigned", "completed"}
                and (maximum is None or attempts < maximum)),
            "available": available, "latest_start_at": latest_start,
        }

    async def detail(self, context, assignment_id, *, cursor=None, limit=25):
        run = await self._run(context, assignment_id)
        can_manage, can_report = await self._can(context, run, "assign"), await self._can(context, run, "report")
        recipient = await self.repository.recipient(context.organization_id, assignment_id, context.principal.user_id)
        if not (can_manage or can_report or recipient):
            raise HTTPException(status_code=403, detail="Assignment permission denied")
        result = self._summary(run)
        result.update({"can_manage": can_manage, "can_report": can_report, "recipients": [], "next_cursor": None})
        if recipient:
            if run["status"] == "closed":
                frozen = await self.repository.frozen_user_rows(context.organization_id, [assignment_id], context.principal.user_id)
                recipient = frozen.get(assignment_id)
                if recipient is None:
                    raise HTTPException(status_code=503, detail="Final completion record is unavailable")
            result["my_assignment"] = self._recipient(recipient, run)
        if can_report:
            result.update((await self._summaries(context, [run]))[0])
            if run["status"] == "closed":
                rows, next_cursor = await self.repository.frozen_recipients(context.organization_id, assignment_id, cursor=cursor, limit=limit)
            else:
                rows, next_cursor = await self.repository.recipient_page(context.organization_id, assignment_id, cursor=cursor, limit=limit)
            result["recipients"] = [self._recipient(row, run) for row in rows]
            result["next_cursor"] = next_cursor
        return result

    async def start(self, context, assignment_id, user):
        await self._run(context, assignment_id)
        recipient = await self.repository.recipient(context.organization_id, assignment_id, context.principal.user_id)
        if recipient is None:
            raise HTTPException(status_code=404, detail="Assigned recipient not found")
        active_session_id = recipient.get("active_session_id")
        if recipient.get("status") == "in_progress" and active_session_id:
            session = await self.repository.attempt(context.organization_id, assignment_id,
                str(recipient["_id"]), context.principal.user_id, active_session_id)
            if session and session.get("status") in {"joined", "active", "disconnected"}:
                if utc(session["expires_at"]) <= now():
                    await self.training.live_quiz_service._ensure_training_expiry_can_finalize(session)
                    quiz = await self.training.live_quiz_service._get_session_quiz(session)
                    if quiz is None:
                        raise HTTPException(status_code=503, detail="Assigned quiz revision is unavailable")
                    await self.training.live_quiz_service._finalize_session(session, quiz, auto_submitted=True)
                else:
                    return await self.training.live_quiz_service.resume_assigned_session(session,
                        user_id=context.principal.user_id, organization_session_id=context.principal.session_id)
        return await self.training.start_assignment(str(recipient["_id"]), user, organization_id=context.organization_id)

    async def close(self, context, assignment_id):
        run = await self._run(context, assignment_id)
        await self._require(context, run, "assign")
        if run["status"] == "closed":
            return await self.detail(context, assignment_id)
        closed = await self.training._close_run(run, context.principal.user_id, require_owner=False)
        if not closed:
            raise HTTPException(status_code=409, detail="Assignment is being finalized")
        return await self.detail(context, assignment_id)

    async def attempts(self, context, assignment_id, user_id, *, cursor=None, limit=25):
        run = await self._run(context, assignment_id)
        await self._require(context, run, "attempt")
        recipient = await self.repository.recipient(context.organization_id, assignment_id, user_id)
        if not recipient:
            raise HTTPException(status_code=404, detail="Assigned recipient not found")
        rows, next_cursor = await self.repository.attempts(context.organization_id, assignment_id, str(recipient["_id"]), user_id, cursor=cursor, limit=limit)
        return {"items": [{"id": str(row["_id"]), **{key: row.get(key) for key in (
            "status", "started_at", "submitted_at", "score", "percentage", "quiz_revision_id", "expires_at",
        )}} for row in rows], "next_cursor": next_cursor}

    async def attempt_detail(self, context, assignment_id, user_id, session_id):
        run = await self._run(context, assignment_id)
        await self._require(context, run, "attempt")
        recipient = await self.repository.recipient(context.organization_id, assignment_id, user_id)
        if not recipient:
            raise HTTPException(status_code=404, detail="Assigned recipient not found")
        session = await self.repository.attempt(context.organization_id, assignment_id, str(recipient["_id"]), user_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Assigned attempt not found")
        if session.get("status") != "submitted":
            raise HTTPException(status_code=409, detail="Attempt has not been submitted")
        return {"id": session_id, "assignment_id": assignment_id, "user_id": user_id,
            **{key: session.get(key) for key in (
                "status", "started_at", "submitted_at", "score", "percentage", "quiz_revision_id", "graded_answers",
            )}, "questions": (session.get("quiz_snapshot") or {}).get("questions", [])}

    async def quizzes(self, context, *, cursor=None, limit=25):
        local = {"organization_id": context.organization_id, "status": {"$ne": "deleted"}}
        # Match CONTENT_READ relationships before pagination, rather than
        # filtering a full page after reading private content.
        if not self.policy.can(context.principal, OrganizationAction.CONTENT_READ,
                {"organization_id": context.organization_id}, context):
            local["$or"] = [{"created_by_user_id": context.principal.user_id}, {"owner_user_id": context.principal.user_id}]
        scopes = [local]
        library = await self.repository.platform_library()
        if library:
            scopes.append({"organization_id": str(library["_id"]), "source": "seed", "visibility": "public", "status": "active"})
        rows, next_cursor = await page(self.training.repository.quizzes_collection, {"$or": scopes},
            cursor=cursor, limit=limit, projection={"title": 1, "quiz_type": 1, "organization_id": 1})
        return {"items": [{"id": str(row["_id"]), "title": row.get("title", "Quiz"), "quiz_type": row.get("quiz_type")} for row in rows], "next_cursor": next_cursor}

    async def recipient_options(self, context, *, cursor=None, limit=25):
        resource = {"organization_id": context.organization_id, "created_by_user_id": context.principal.user_id}
        if not self.policy.can(context.principal, OrganizationAction.ASSIGNMENT_CREATE, resource, context):
            raise HTTPException(status_code=403, detail="Assignment permission denied")
        rows, next_cursor = await self.repository.recipient_options(
            context.organization_id, cursor=cursor, limit=limit)
        return {"items": [{"user_id": row["user_id"], "name": row["name"]} for row in rows],
                "next_cursor": next_cursor}
