from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
import secrets
import string
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from server.app.core.config import settings
from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.users.identity import normalize_email


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class TrainingRunService:
    """Creates accountable training deliveries without changing public live quizzes."""

    def __init__(
        self,
        repository: TrainingRunRepository,
        live_quiz_service: LiveQuizSessionService,
        notification_service=None,
    ):
        self.repository = repository
        self.live_quiz_service = live_quiz_service
        self.notification_service = notification_service

    async def list_owned_quizzes(self, owner_user_id: str) -> list[dict]:
        quizzes = await self.repository.list_owned_quizzes(owner_user_id)
        return [
            {
                "id": str(quiz["_id"]),
                "title": quiz.get("title", "Untitled quiz"),
                "quiz_type": str(quiz.get("quiz_type", "multichoice")),
                "created_at": quiz.get("created_at"),
            }
            for quiz in quizzes
        ]

    async def create_run(self, payload, owner_user_id: str) -> dict:
        now = _utc_now()
        closes_at = _as_utc(payload.closes_at)
        due_at = _as_utc(payload.due_at) if payload.due_at else None
        if closes_at <= now:
            raise HTTPException(status_code=400, detail="Run close time must be in the future")
        if closes_at <= now + timedelta(minutes=payload.time_limit_minutes):
            raise HTTPException(
                status_code=400,
                detail="Run close time must allow one full training duration",
            )

        quiz = await self.repository.get_owned_quiz(payload.quiz_id, owner_user_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Owned quiz not found")
        if not quiz.get("questions"):
            raise HTTPException(status_code=400, detail="Quiz has no questions")

        access_code = (
            await self._generate_unique_code()
            if payload.access_mode == "public"
            else None
        )
        title = (payload.title or "").strip() or quiz.get("title") or "Training run"
        quiz_snapshot = self._quiz_snapshot(quiz)
        recipient_user_ids = (
            await self.notification_service.verified_user_ids_by_email(
                [str(email) for email in payload.recipient_emails]
            )
            if self.notification_service
            else {}
        )
        run = await self.repository.create_run(
            {
                "quiz_id": str(quiz["_id"]),
                "owner_user_id": owner_user_id,
                "title": title,
                "kind": payload.kind,
                "purpose": payload.purpose,
                "status": "open",
                "access_mode": payload.access_mode,
                "access_code": access_code,
                "time_limit_minutes": payload.time_limit_minutes,
                "due_at": due_at,
                "closes_at": closes_at,
                "closed_at": None,
                "quiz_content_fingerprint": quiz.get("content_fingerprint"),
                "quiz_snapshot": quiz_snapshot,
                "created_at": now,
                "updated_at": now,
            }
        )
        run_id = str(run["_id"])
        assignments = [
            {
                "_id": ObjectId(),
                "training_run_id": run_id,
                "quiz_id": str(quiz["_id"]),
                "owner_user_id": owner_user_id,
                "recipient_email": normalize_email(str(email)),
                "recipient_user_id": recipient_user_ids.get(normalize_email(str(email))),
                "status": "assigned",
                "due_at": due_at,
                "max_attempts": payload.max_attempts,
                "attempts_used": 0,
                "started_at": None,
                "completed_at": None,
                "latest_session_id": None,
                "latest_score": None,
                "latest_percentage": None,
                "created_at": now,
                "updated_at": now,
            }
            for email in payload.recipient_emails
        ]
        await self.repository.create_assignments(assignments)
        if self.notification_service:
            await self.notification_service.notify_assignments(assignments, run)
        await self.repository.create_audit_event(
            {
                "training_run_id": run_id,
                "event_type": "run_created",
                "actor_user_id": owner_user_id,
                "occurred_at": now,
                "payload": {
                    "kind": payload.kind,
                    "purpose": payload.purpose,
                    "recipient_count": len(assignments),
                    "closes_at": closes_at,
                },
            }
        )
        if payload.send_email_invitations and assignments:
            await self.repository.create_invitation_deliveries(
                self._invitation_deliveries(run, assignments, now)
            )
            self._enqueue_invitation_delivery_dispatch()
        return self._run_summary(run, assignments, [])

    async def list_owner_runs(self, owner_user_id: str) -> list[dict]:
        runs = await self.repository.list_runs_for_owner(owner_user_id)
        summaries = []
        for run in runs:
            assignments = await self.repository.list_assignments_for_run(str(run["_id"]))
            sessions = await self.repository.list_sessions_for_run(str(run["_id"]))
            summaries.append(self._run_summary(run, assignments, sessions))
        return summaries

    async def get_owner_run(self, run_id: str, owner_user_id: str) -> dict:
        run = await self.repository.get_run(run_id)
        if not run or run.get("owner_user_id") != owner_user_id:
            raise HTTPException(status_code=404, detail="Training run not found")
        assignments = await self.repository.list_assignments_for_run(run_id)
        sessions = await self.repository.list_sessions_for_run(run_id)
        summary = self._run_summary(run, assignments, sessions)
        summary["completion_register"] = [
            *[self._completion_row(assignment) for assignment in assignments],
            *[
                self._shared_session_row(session)
                for session in sessions
                if not session.get("training_assignment_id")
            ],
        ]
        return summary

    async def close_owner_run(self, run_id: str, owner_user_id: str) -> dict:
        run = await self.repository.get_run(run_id)
        if not run or run.get("owner_user_id") != owner_user_id:
            raise HTTPException(status_code=404, detail="Training run not found")
        closed = await self._close_run(run, owner_user_id)
        if not closed:
            current = await self.repository.get_run(run_id)
            detail = (
                "Training run is being finalized"
                if current and current.get("closure_in_progress")
                else "Training run is already closed"
            )
            raise HTTPException(status_code=409, detail=detail)
        assignments = await self.repository.list_assignments_for_run(run_id)
        sessions = await self.repository.list_sessions_for_run(run_id)
        return self._run_summary(closed, assignments, sessions)

    async def list_my_assignments(self, user_id: str, email: str) -> list[dict]:
        normalized_email = normalize_email(email)
        newly_bound = await self.repository.bind_assignments_to_user(normalized_email, user_id)
        for assignment in newly_bound:
            run = await self.repository.get_run(assignment["training_run_id"])
            if run:
                await self._notify_assignment_safely(assignment, run, user_id)
        assignments = await self.repository.list_assignments_for_recipient(normalized_email, user_id)
        result = []
        for assignment in assignments:
            run = await self.repository.get_run(assignment["training_run_id"])
            if not run:
                continue
            result.append(self._assignment_summary(assignment, run))
        return result

    async def start_assignment(self, assignment_id: str, user) -> dict:
        normalized_email = normalize_email(str(user.email))
        user_id = str(user.id)
        newly_bound = await self.repository.bind_assignments_to_user(normalized_email, user_id)
        for newly_bound_assignment in newly_bound:
            bound_run = await self.repository.get_run(newly_bound_assignment["training_run_id"])
            if bound_run:
                await self._notify_assignment_safely(
                    newly_bound_assignment, bound_run, user_id
                )
        assignment = await self.repository.get_assignment(assignment_id)
        if not assignment or assignment.get("recipient_user_id") != user_id:
            raise HTTPException(status_code=404, detail="Training assignment not found")
        run = await self.repository.get_run(assignment["training_run_id"])
        if not run:
            raise HTTPException(status_code=404, detail="Training run not found")
        if run.get("status") != "open" or run.get("closure_in_progress"):
            raise HTTPException(status_code=409, detail="Training run is closed")
        if _as_utc(run["closes_at"]) <= _utc_now():
            raise HTTPException(status_code=409, detail="Training run is closed")
        self._ensure_enough_time_to_start(run)
        quiz = await self._quiz_for_run(run)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz for training run not found")
        reserved = await self.repository.reserve_attempt(assignment_id, user_id, _utc_now())
        if not reserved:
            raise HTTPException(status_code=409, detail="No attempts remain for this assignment")
        try:
            return await self.live_quiz_service.start_session_for_quiz(
                quiz,
                participant_name=user.full_name or user.username,
                participant_email=normalized_email,
                time_limit_minutes=run["time_limit_minutes"],
                training_run_id=str(run["_id"]),
                training_assignment_id=assignment_id,
                user_id=user_id,
                participant_type="assigned",
                quiz_snapshot=run.get("quiz_snapshot"),
                training_closes_at=run["closes_at"],
            )
        except Exception:
            await self.repository.release_attempt(
                assignment_id,
                user_id,
                previous_status=assignment["status"],
                previous_started_at=assignment.get("started_at"),
                now=_utc_now(),
            )
            raise

    async def access_preview(self, access_code: str) -> dict:
        run, quiz = await self._get_public_startable_run(access_code)
        return {
            "title": run["title"],
            "total_questions": len(quiz.get("questions") or []),
            "time_limit_minutes": run["time_limit_minutes"],
            "closes_at": _as_utc(run["closes_at"]),
        }

    async def start_shared_session(self, access_code: str, participant_name: str, participant_email: Optional[str]) -> dict:
        run, quiz = await self._get_public_startable_run(access_code)
        self._ensure_enough_time_to_start(run)
        return await self.live_quiz_service.start_session_for_quiz(
            quiz,
            participant_name=participant_name,
            participant_email=normalize_email(participant_email) if participant_email else None,
            time_limit_minutes=run["time_limit_minutes"],
            training_run_id=str(run["_id"]),
            participant_type="guest",
            quiz_snapshot=run.get("quiz_snapshot"),
            training_closes_at=run["closes_at"],
        )

    async def _get_public_startable_run(self, access_code: str) -> tuple[dict, dict]:
        run = await self.repository.get_run_by_access_code(access_code)
        if not run:
            raise HTTPException(status_code=404, detail="Training run not found")
        if run.get("status") != "open" or run.get("closure_in_progress"):
            raise HTTPException(status_code=410, detail="Training run is closed")
        # The worker writes the final audit snapshot, but public access must stop
        # immediately at the configured boundary rather than waiting for its next run.
        if _as_utc(run["closes_at"]) <= _utc_now():
            raise HTTPException(status_code=410, detail="Training run is closed")
        if run.get("access_mode") != "public":
            raise HTTPException(status_code=403, detail="This training is available from an assignment")
        quiz = await self._quiz_for_run(run)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz for training run not found")
        return run, quiz

    async def _close_run(self, run: dict, owner_user_id: Optional[str]) -> Optional[dict]:
        closed_at = _utc_now()
        claimed = await self.repository.claim_run_closure(
            str(run["_id"]), owner_user_id, closed_at
        )
        if not claimed:
            return None
        try:
            # Manual closure is an immediate cutoff, not an implicit partial
            # submission. Persist terminal states before the immutable snapshot.
            await self.repository.mark_in_progress_assignments_incomplete(
                str(claimed["_id"]), closed_at
            )
            await self.repository.abandon_active_sessions_for_run(
                str(claimed["_id"]), closed_at
            )
            assignments = await self.repository.list_assignments_for_run(str(claimed["_id"]))
            sessions = await self.repository.list_sessions_for_run(str(claimed["_id"]))
            await self.repository.create_audit_event(
                {
                    "training_run_id": str(claimed["_id"]),
                    "event_type": "run_closed",
                    "actor_user_id": owner_user_id,
                    "occurred_at": closed_at,
                    # No update/delete operation is exposed for a final audit snapshot.
                    "payload": {
                        "run": {
                            "quiz_id": claimed["quiz_id"],
                            "title": claimed["title"],
                            "kind": claimed["kind"],
                            "purpose": claimed["purpose"],
                            "quiz_content_fingerprint": claimed.get("quiz_content_fingerprint"),
                            "quiz_snapshot": claimed.get("quiz_snapshot"),
                            "closes_at": claimed["closes_at"],
                        },
                        "completion_register": [
                            *[self._audit_assignment_row(item) for item in assignments],
                            *[
                                self._audit_shared_session_row(session)
                                for session in sessions
                                if not session.get("training_assignment_id")
                            ],
                        ],
                    },
                }
            )
            closed = await self.repository.finalize_run_closure(
                str(claimed["_id"]), owner_user_id, closed_at
            )
            if not closed:
                raise RuntimeError("Training run closure could not be finalized")
            return closed
        except Exception:
            await self.repository.release_run_closure(str(claimed["_id"]), owner_user_id)
            raise

    @staticmethod
    def _quiz_snapshot(quiz: dict) -> dict:
        quiz_type = quiz.get("quiz_type")
        return {
            "title": quiz.get("title", "Training quiz"),
            "quiz_type": getattr(quiz_type, "value", quiz_type),
            "questions": deepcopy(quiz.get("questions") or []),
        }

    async def _quiz_for_run(self, run: dict) -> Optional[dict]:
        snapshot = run.get("quiz_snapshot")
        if snapshot and snapshot.get("questions"):
            return {
                **deepcopy(snapshot),
                "_id": run["quiz_id"],
                "owner_user_id": run["owner_user_id"],
            }
        return await self.repository.get_owned_quiz(run["quiz_id"], run["owner_user_id"])

    async def _notify_assignment_safely(
        self, assignment: dict, run: dict, user_id: str
    ) -> None:
        if not self.notification_service:
            return
        try:
            await self.notification_service.notify_assignment(assignment, run, user_id)
        except Exception:
            logger.exception(
                "Could not create training assignment notification for assignment %s",
                assignment["_id"],
            )

    @staticmethod
    def _ensure_enough_time_to_start(run: dict) -> None:
        latest_start = _as_utc(run["closes_at"]) - timedelta(
            minutes=int(run["time_limit_minutes"])
        )
        if _utc_now() >= latest_start:
            raise HTTPException(
                status_code=409,
                detail="There is not enough time left to complete this training before it closes",
            )

    def _run_summary(self, run: dict, assignments: list[dict], sessions: list[dict]) -> dict:
        completed = [item for item in assignments if item.get("status") == "completed"]
        started = [
            item
            for item in assignments
            if item.get("status") in {"in_progress", "incomplete", "completed"}
        ]
        shared_sessions = [item for item in sessions if not item.get("training_assignment_id")]
        shared_completed = [item for item in shared_sessions if item.get("status") == "submitted"]
        scores = [
            *[item["latest_score"] for item in completed if isinstance(item.get("latest_score"), int)],
            *[item["score"] for item in shared_completed if isinstance(item.get("score"), int)],
        ]
        code = run.get("access_code")
        return {
            "id": str(run["_id"]), "quiz_id": run["quiz_id"], "title": run["title"],
            "kind": run["kind"], "purpose": run["purpose"], "status": run["status"],
            "access_mode": run["access_mode"], "access_code": code,
            "access_url": f"{settings.FRONTEND_BASE_URL}/training-access/{code}" if code else None,
            "time_limit_minutes": run["time_limit_minutes"], "due_at": run.get("due_at"),
            "closes_at": run["closes_at"], "closed_at": run.get("closed_at"),
            "created_at": run["created_at"], "assigned_count": len(assignments),
            "started_count": len(started) + len(shared_sessions),
            "completed_count": len(completed) + len(shared_completed),
            "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        }

    def _assignment_summary(self, assignment: dict, run: dict) -> dict:
        now = _utc_now()
        due_at = assignment.get("due_at")
        max_attempts = assignment.get("max_attempts")
        attempts_used = int(assignment.get("attempts_used", 0))
        latest_start_at = _as_utc(run["closes_at"]) - timedelta(
            minutes=int(run["time_limit_minutes"])
        )
        return {
            "id": str(assignment["_id"]), "training_run_id": assignment["training_run_id"],
            "quiz_id": assignment["quiz_id"], "title": run["title"], "kind": run["kind"],
            "purpose": run["purpose"], "status": assignment["status"], "due_at": due_at,
            "closes_at": run["closes_at"], "latest_start_at": latest_start_at,
            "is_overdue": bool(due_at and _as_utc(due_at) < now and assignment.get("status") != "completed"),
            "max_attempts": max_attempts, "attempts_used": attempts_used,
            "can_retry": (
                run.get("status") == "open"
                and now <= latest_start_at
                and (max_attempts is None or attempts_used < max_attempts)
            ),
            "latest_score": assignment.get("latest_score"),
            "latest_percentage": assignment.get("latest_percentage"),
            "completed_at": assignment.get("completed_at"),
        }

    @staticmethod
    def _completion_row(assignment: dict) -> dict:
        return {
            "assignment_id": str(assignment["_id"]), "recipient_email": assignment["recipient_email"],
            "recipient_name": assignment.get("recipient_name"), "status": assignment["status"],
            "due_at": assignment.get("due_at"), "attempts_used": assignment.get("attempts_used", 0),
            "max_attempts": assignment.get("max_attempts"), "started_at": assignment.get("started_at"),
            "completed_at": assignment.get("completed_at"), "latest_score": assignment.get("latest_score"),
            "latest_percentage": assignment.get("latest_percentage"),
        }

    @staticmethod
    def _shared_session_row(session: dict) -> dict:
        return {
            "assignment_id": str(session["_id"]),
            "recipient_email": session.get("participant_email"),
            "recipient_name": session.get("participant_name"),
            "status": (
                "completed"
                if session.get("status") == "submitted"
                else "incomplete"
                if session.get("status") == "abandoned"
                else "in_progress"
            ),
            "due_at": None,
            "attempts_used": 1,
            "max_attempts": None,
            "started_at": session.get("started_at"),
            "completed_at": session.get("submitted_at"),
            "latest_score": session.get("score"),
            "latest_percentage": session.get("percentage"),
        }

    @staticmethod
    def _audit_assignment_row(assignment: dict) -> dict:
        return {
            "assignment_id": str(assignment["_id"]), "recipient_email": assignment["recipient_email"],
            "status": assignment["status"], "attempts_used": assignment.get("attempts_used", 0),
            "max_attempts": assignment.get("max_attempts"), "started_at": assignment.get("started_at"),
            "completed_at": assignment.get("completed_at"), "latest_score": assignment.get("latest_score"),
            "latest_percentage": assignment.get("latest_percentage"),
        }

    @staticmethod
    def _audit_shared_session_row(session: dict) -> dict:
        return {
            "session_id": str(session["_id"]),
            "participant_name": session.get("participant_name"),
            "participant_email": session.get("participant_email"),
            "status": session.get("status"),
            "started_at": session.get("started_at"),
            "submitted_at": session.get("submitted_at"),
            "score": session.get("score"),
            "percentage": session.get("percentage"),
        }

    async def _generate_unique_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if not await self.repository.access_code_exists_on_run(code) and not await self.repository.access_code_exists_on_quiz(code):
                return code
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate training access code")

    @staticmethod
    def _invitation_deliveries(
        run: dict, assignments: list[dict], now: datetime
    ) -> list[dict]:
        due_text = (
            _as_utc(run["due_at"]).strftime("%d %b %Y, %H:%M UTC")
            if run.get("due_at")
            else "before the run closes"
        )
        return [
            {
                "delivery_key": (
                    f"training-run:{run['_id']}:recipient:"
                    f"{assignment['recipient_email']}:invitation"
                ),
                "training_run_id": str(run["_id"]),
                "recipient_email": assignment["recipient_email"],
                "template_id": "custom",
                "template_vars": {
                    "subject": f"Training assigned: {run['title']}",
                    "body": (
                        f"You have been assigned {run['title']}. Sign in with this email "
                        f"to complete it by {due_text}.\n\n"
                        f"{settings.FRONTEND_BASE_URL}/assigned-training"
                    ),
                },
                "purpose": "training_invitation",
                "status": "pending",
                "attempt_count": 0,
                "next_attempt_at": now,
                "lease_expires_at": None,
                "last_error": None,
                "provider": None,
                "provider_message_id": None,
                "sent_at": None,
                "created_at": now,
                "updated_at": now,
            }
            for assignment in assignments
        ]

    @staticmethod
    def _enqueue_invitation_delivery_dispatch() -> None:
        try:
            from server.celery_config import celery_app

            celery_app.send_task(
                "tasks.dispatch_training_invitation_deliveries",
                queue="email",
                ignore_result=True,
            )
        except Exception:
            # The periodic dispatcher will recover any durable pending records.
            logger.exception("Could not enqueue training invitation delivery dispatch")
