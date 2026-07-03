from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
import string
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import EmailStr, TypeAdapter, ValidationError

from server.app.quiz.utils.grading import grade_answers
from server.app.quiz.repositories.live_session_repository import (
    LiveQuizSessionRepository,
)
from server.app.quiz.services.live_quiz_realtime import LiveQuizRealtimeBroadcaster


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LiveQuizSessionService:
    def __init__(
        self,
        repository: LiveQuizSessionRepository,
        broadcaster: Optional[LiveQuizRealtimeBroadcaster] = None,
    ):
        self.repository = repository
        self.broadcaster = broadcaster

    async def generate_access_code(
        self,
        quiz_id: str,
        access_code_expires_at: datetime,
        creator_id: str,
        time_limit_minutes: int,
        participant_access_mode: str = "public",
        invited_emails: Optional[List[str]] = None,
        send_email_invitations: bool = False,
        invitation_repository=None,
        email_service=None,
        frontend_origin: Optional[str] = None,
    ) -> Dict[str, Any]:
        quiz = await self.repository.get_quiz_by_id(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        owner_id = quiz.get("owner_user_id") or quiz.get("created_by") or quiz.get("owner_id")
        if not owner_id or str(owner_id) != creator_id:
            raise HTTPException(status_code=403, detail="Not allowed")

        existing_access_code = quiz.get("access_code")
        existing_expiration = quiz.get("access_code_expires_at")
        if (
            quiz.get("live_quiz_enabled")
            and existing_access_code
            and existing_expiration
            and _as_utc(existing_expiration) > _utc_now()
        ):
            invited = [
                email.strip().lower()
                for email in quiz.get("invited_participant_emails", [])
                if email
            ]
            return {
                "quiz_id": str(quiz["_id"]),
                "access_code": existing_access_code,
                "live_quiz_enabled": True,
                "time_limit_minutes": quiz.get("time_limit_minutes") or time_limit_minutes,
                "access_code_expires_at": _as_utc(existing_expiration),
                "participant_access_mode": quiz.get("participant_access_mode", "public"),
                "invited_emails": invited,
                "invitations_created": len(invited),
                "invitations_delivered": 0,
            }

        if _as_utc(access_code_expires_at) <= _utc_now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access code expiration must be in the future",
            )

        normalized_invited_emails = self._normalize_invited_emails(invited_emails or [])
        if participant_access_mode not in {"public", "restricted", "invited_only"}:
            raise HTTPException(status_code=400, detail="Invalid participant access mode")
        if participant_access_mode in {"restricted", "invited_only"} and not normalized_invited_emails:
            raise HTTPException(
                status_code=400,
                detail="Restricted live quizzes require at least one invited email",
            )

        code = await self._generate_unique_code()
        updated_quiz = await self.repository.enable_live_quiz(
            quiz_id=quiz_id,
            access_code=code,
            time_limit_minutes=time_limit_minutes,
            access_code_expires_at=_as_utc(access_code_expires_at),
            creator_id=creator_id,
            participant_access_mode=participant_access_mode,
            invited_participant_emails=normalized_invited_emails,
        )
        if not updated_quiz:
            raise HTTPException(status_code=500, detail="Could not enable live quiz")

        invitations_created = 0
        invitations_delivered = 0
        if invitation_repository and normalized_invited_emails:
            title = updated_quiz.get("title", "Live Quiz")
            join_link = self._join_link(code, frontend_origin)
            for email in normalized_invited_emails:
                invitation_id = await invitation_repository.upsert_invitation(
                    {
                        "quiz_id": str(updated_quiz["_id"]),
                        "creator_user_id": creator_id,
                        "access_code": code,
                        "email": email,
                        "status": "pending",
                        "session_id": None,
                        "email_sent": False,
                        "email_sent_at": None,
                        "invitation_sent_status": "pending",
                    }
                )
                invitations_created += 1
                if send_email_invitations and email_service:
                    try:
                        await email_service.send_email(
                            to=email,
                            template_id="custom",
                            template_vars={
                                "subject": f"Invitation: {title}",
                                "body": self._invitation_email_body(
                                    title=title,
                                    access_code=code,
                                    join_link=join_link,
                                    starts_at=None,
                                    ends_at=_as_utc(access_code_expires_at),
                                    time_limit_minutes=time_limit_minutes,
                                ),
                            },
                            purpose="live_quiz_invitation",
                            priority="default",
                        )
                        await invitation_repository.update_email_delivery(
                            invitation_id,
                            email_sent=True,
                            invitation_sent_status="delivered",
                            status="delivered",
                        )
                        invitations_delivered += 1
                    except Exception as e:
                        logger.warning(f"Could not send live quiz invitation to {email}: {e}")
                        await invitation_repository.update_email_delivery(
                            invitation_id,
                            email_sent=False,
                            invitation_sent_status="failed",
                        )

        return {
            "quiz_id": str(updated_quiz["_id"]),
            "access_code": code,
            "live_quiz_enabled": True,
            "time_limit_minutes": time_limit_minutes,
            "access_code_expires_at": _as_utc(updated_quiz["access_code_expires_at"]),
            "participant_access_mode": participant_access_mode,
            "invited_emails": normalized_invited_emails,
            "invitations_created": invitations_created,
            "invitations_delivered": invitations_delivered,
        }

    async def validate_access_code(self, code: str) -> Dict[str, Any]:
        quiz = await self._get_startable_quiz(code)
        questions = quiz.get("questions") or []
        return {
            "quiz_id": str(quiz["_id"]),
            "title": quiz.get("title", "Live Quiz"),
            "total_questions": len(questions),
            "time_limit_minutes": quiz["time_limit_minutes"],
            "access_code_expires_at": _as_utc(quiz["access_code_expires_at"]),
            "participant_access_mode": quiz.get("participant_access_mode", "public"),
        }

    async def start_session(
        self,
        code: str,
        participant_name: str,
        participant_email: Optional[str],
        invitation_repository=None,
    ) -> Dict[str, Any]:
        quiz = await self._get_startable_quiz(code)
        questions = quiz.get("questions") or []
        if not questions:
            raise HTTPException(status_code=400, detail="Quiz has no questions")

        if not participant_name or not participant_name.strip():
            raise HTTPException(status_code=400, detail="Participant name is required")

        normalized_email = participant_email.strip().lower() if participant_email else ""

        # Check access mode
        access_mode = quiz.get("participant_access_mode", "public")
        if access_mode in {"invited_only", "restricted"}:
            if not participant_email:
                raise HTTPException(
                    status_code=400,
                    detail="Email is required for restricted access mode",
                )
            invited_emails = [e.strip().lower() for e in quiz.get("invited_participant_emails", [])]
            if normalized_email not in invited_emails:
                # Also check invitation collection if available
                if invitation_repository:
                    is_invited = await invitation_repository.invitation_exists_for_quiz(
                        str(quiz["_id"]), normalized_email
                    )
                    if not is_invited:
                        raise HTTPException(
                            status_code=403,
                            detail="This email is not invited to take this quiz",
                        )
                else:
                    raise HTTPException(
                        status_code=403,
                        detail="This email is not invited to take this quiz",
                    )
        # For public mode, email is still helpful - require it but soft
        # (spec says recommended for both modes)

        participant_token = secrets.token_urlsafe(32)
        started_at = _utc_now()
        time_limit_minutes = int(quiz["time_limit_minutes"])
        duration_seconds = time_limit_minutes * 60
        expires_at = started_at + timedelta(minutes=time_limit_minutes)
        server_now = started_at
        guest_id = f"guest_{secrets.token_urlsafe(12)}"

        creator_user_id = quiz.get("owner_user_id") or quiz.get("created_by") or quiz.get("owner_id")

        session_data = {
            "quiz_id": str(quiz["_id"]),
            "creator_user_id": creator_user_id,
            "participant_type": "guest",
            "user_id": None,
            "participant_name": participant_name.strip(),
            "participant_email": normalized_email if normalized_email else None,
            "guest_id": guest_id,
            "participant_token_hash": _hash_token(participant_token),
            "started_at": started_at,
            "joined_at": started_at,
            "expires_at": expires_at,
            "submitted_at": None,
            "status": "joined",
            "current_question_index": 0,
            "answers": [],
            "score": None,
            "total_questions": len(questions),
            "duration_seconds": duration_seconds,
            "duration_used_seconds": None,
            "percentage": None,
            "auto_submitted": False,
            "created_at": started_at,
            "updated_at": started_at,
        }
        session_id = await self.repository.create_session(session_data)
        remaining_seconds = self._remaining_seconds(expires_at, server_now)

        # Update invitation status if invitation repository is available
        if invitation_repository and normalized_email:
            try:
                await invitation_repository.update_status(
                    quiz_id=str(quiz["_id"]),
                    email=normalized_email,
                    status="joined",
                    session_id=session_id,
                    name=participant_name.strip(),
                )
            except Exception as e:
                logger.warning(f"Could not update invitation status: {e}")

        logger.info(
            {
                "event": "live_quiz_session_started",
                "session_id": session_id,
                "started_at": started_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "server_now": server_now.isoformat(),
                "time_limit_minutes": time_limit_minutes,
                "remaining_seconds": remaining_seconds,
                "creator_user_id": creator_user_id,
            }
        )
        response = {
            "session_id": session_id,
            "participant_token": participant_token,
            "started_at": started_at,
            "expires_at": expires_at,
            "server_now": server_now,
            "time_limit_minutes": time_limit_minutes,
            "duration_seconds": duration_seconds,
            "remaining_seconds": remaining_seconds,
            "redirect_url": f"/live-quiz/{session_id}",
        }
        await self._publish_participant_event(str(quiz["_id"]), session_id, "participant_joined")
        return response

    async def get_session_state(
        self,
        session_id: str,
        participant_token: str,
    ) -> Dict[str, Any]:
        session = await self._get_authorized_session(session_id, participant_token)
        quiz = await self.repository.get_quiz_by_id(session["quiz_id"])
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if self._is_expired(session) and session.get("status") in {"active", "joined", "disconnected"}:
            session = await self._finalize_session(
                session,
                quiz,
                auto_submitted=True,
            )
            await self._publish_participant_event(
                session["quiz_id"],
                str(session["_id"]),
                "participant_submitted",
            )

        return self._build_session_state(session, quiz)

    async def save_answer(
        self,
        session_id: str,
        participant_token: str,
        question_index: int,
        selected_answer: str,
        next_question_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        session = await self._get_authorized_session(session_id, participant_token)
        if session.get("status") not in {"active", "joined", "disconnected"}:
            raise HTTPException(status_code=409, detail="Session is not active")
        if self._is_expired(session):
            quiz = await self.repository.get_quiz_by_id(session["quiz_id"])
            if quiz:
                await self._finalize_session(session, quiz, auto_submitted=True)
            raise HTTPException(status_code=409, detail="Session has expired")
        if question_index < 0 or question_index >= session["total_questions"]:
            raise HTTPException(status_code=400, detail="Invalid question index")

        next_index = (
            next_question_index
            if next_question_index is not None
            else session["current_question_index"]
        )
        if next_index < 0 or next_index >= session["total_questions"]:
            raise HTTPException(status_code=400, detail="Invalid next question index")
        updated = await self.repository.save_answer(
            session_id,
            question_index,
            selected_answer,
            next_index,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        await self._publish_participant_event(
            updated["quiz_id"],
            str(updated["_id"]),
            "participant_progress",
        )
        return {
            "status": updated["status"],
            "current_question_index": updated["current_question_index"],
            "remaining_seconds": self._remaining_seconds(updated["expires_at"]),
        }

    async def submit_session(
        self,
        session_id: str,
        participant_token: str,
        auto_submitted: bool = False,
        invitation_repository=None,
    ) -> Dict[str, Any]:
        session = await self._get_authorized_session(session_id, participant_token)
        quiz = await self.repository.get_quiz_by_id(session["quiz_id"])
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if session.get("status") == "submitted":
            return self._submission_response(session, already_submitted=True)

        is_expired = self._is_expired(session)
        if auto_submitted and not is_expired:
            logger.info(
                {
                    "event": "live_quiz_auto_submit_rejected_before_expiry",
                    "session_id": session_id,
                    "server_now": _utc_now().isoformat(),
                    "expires_at": _as_utc(session["expires_at"]).isoformat(),
                    "remaining_seconds": self._remaining_seconds(session["expires_at"]),
                }
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session has not expired",
            )

        finalized = await self._finalize_session(
            session,
            quiz,
            auto_submitted=auto_submitted or is_expired,
        )

        # Update invitation status if available
        if invitation_repository:
            participant_email = session.get("participant_email")
            if participant_email:
                try:
                    inv_status = "completed" if not auto_submitted else "expired"
                    await invitation_repository.update_status(
                        quiz_id=session["quiz_id"],
                        email=participant_email,
                        status=inv_status,
                        session_id=session_id,
                    )
                except Exception as e:
                    logger.warning(f"Could not update invitation status on submit: {e}")

        await self._publish_participant_event(
            finalized["quiz_id"],
            str(finalized["_id"]),
            "participant_submitted",
        )
        return self._submission_response(finalized)

    async def mark_disconnected(
        self,
        session_id: str,
        participant_token: str,
    ) -> Dict[str, Any]:
        session = await self._get_authorized_session(session_id, participant_token)
        if session.get("status") not in {"active", "joined"}:
            return {"status": session.get("status")}

        updated = await self.repository.update_session(
            session_id,
            {"status": "disconnected"},
        )
        if updated:
            await self._publish_participant_event(
                updated["quiz_id"],
                str(updated["_id"]),
                "participant_disconnected",
            )
            return {"status": "disconnected"}
        return {"status": session.get("status")}

    async def list_analytics(self, quiz_id: str, requester_id: str) -> List[Dict[str, Any]]:
        quiz = await self.repository.get_quiz_by_id(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        owner_id = quiz.get("created_by") or quiz.get("owner_id") or quiz.get("owner_user_id")
        if not owner_id or str(owner_id) != requester_id:
            raise HTTPException(status_code=403, detail="Not allowed")

        sessions = await self.repository.list_quiz_sessions(quiz_id)
        return [self._analytics_row(session) for session in sessions]

    async def list_creator_live_quizzes(
        self,
        creator_user_id: str,
    ) -> List[Dict[str, Any]]:
        quizzes = await self.repository.list_live_quizzes_by_creator(creator_user_id)
        rows = []
        for quiz in quizzes:
            quiz_id = str(quiz["_id"])
            sessions = await self.repository.list_quiz_sessions(quiz_id)
            completed = [
                session
                for session in sessions
                if session.get("submitted_at") or session.get("status") == "submitted"
            ]
            scores = [
                session.get("score")
                for session in completed
                if isinstance(session.get("score"), int)
            ]
            rows.append(
                {
                    "quiz_id": quiz_id,
                    "title": quiz.get("title", "Live Quiz"),
                    "access_code": quiz.get("access_code"),
                    "access_code_expires_at": quiz.get("access_code_expires_at"),
                    "time_limit_minutes": quiz.get("time_limit_minutes"),
                    "participant_access_mode": quiz.get(
                        "participant_access_mode", "public"
                    ),
                    "invited_emails": quiz.get("invited_participant_emails", []),
                    "status": self._quiz_status(quiz, sessions),
                    "created_at": quiz.get("created_at"),
                    "participant_count": len(sessions),
                    "completed_count": len(completed),
                    "average_score": round(sum(scores) / len(scores), 2)
                    if scores
                    else None,
                }
            )
        return rows

    async def _generate_unique_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(6))
            if not await self.repository.access_code_exists(code):
                return code
        raise HTTPException(status_code=500, detail="Could not generate access code")

    async def _get_startable_quiz(self, code: str) -> Dict[str, Any]:
        quiz = await self.repository.get_quiz_by_access_code(code)
        if not quiz or not quiz.get("live_quiz_enabled"):
            raise HTTPException(status_code=404, detail="Live quiz not found")

        expires_at = quiz.get("access_code_expires_at")
        if not expires_at or _as_utc(expires_at) <= _utc_now():
            raise HTTPException(status_code=410, detail="Access code has expired")
        if not quiz.get("time_limit_minutes"):
            raise HTTPException(status_code=400, detail="Quiz time limit is not configured")
        return quiz

    async def _get_authorized_session(
        self,
        session_id: str,
        participant_token: str,
    ) -> Dict[str, Any]:
        if not participant_token:
            raise HTTPException(status_code=401, detail="Participant token missing")
        session = await self.repository.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.get("participant_token_hash") != _hash_token(participant_token):
            raise HTTPException(status_code=403, detail="Invalid participant token")
        return session

    async def _finalize_session(
        self,
        session: Dict[str, Any],
        quiz: Dict[str, Any],
        auto_submitted: bool,
    ) -> Dict[str, Any]:
        graded = self._grade_session(session, quiz)
        submitted_at = _utc_now()

        # Calculate duration_used_seconds
        started_at = _as_utc(session["started_at"])
        duration_used_seconds = int((submitted_at - started_at).total_seconds())

        updated = await self.repository.update_session(
            str(session["_id"]),
            {
                "status": "submitted",
                "submitted_at": submitted_at,
                "score": graded["score"],
                "percentage": graded["percentage"],
                "duration_used_seconds": duration_used_seconds,
                "auto_submitted": auto_submitted,
            },
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        return updated

    def _grade_session(
        self,
        session: Dict[str, Any],
        quiz: Dict[str, Any],
    ) -> Dict[str, Any]:
        questions = quiz.get("questions") or []
        answer_by_index = {
            answer["question_index"]: answer.get("selected_answer", "")
            for answer in session.get("answers", [])
        }
        grading_payload = []
        for index, question in enumerate(questions):
            correct_answer = question.get("correct_answer") or question.get("answer")
            grading_payload.append(
                {
                    "question": question.get("question", ""),
                    "user_answer": answer_by_index.get(index, ""),
                    "correct_answer": correct_answer,
                    "question_type": question.get("question_type")
                    or quiz.get("quiz_type")
                    or "multichoice",
                    "source": question.get("source", "live"),
                }
            )

        graded_answers = grade_answers(grading_payload, "mock")
        score = sum(1 for answer in graded_answers if answer.get("is_correct"))
        total = len(questions)
        percentage = round((score / total) * 100, 2) if total else 0
        return {"score": score, "percentage": percentage}

    def _build_session_state(
        self,
        session: Dict[str, Any],
        quiz: Dict[str, Any],
    ) -> Dict[str, Any]:
        current_index = session.get("current_question_index", 0)
        questions = quiz.get("questions") or []
        question = None
        if session.get("status") in {"active", "joined", "disconnected"} and 0 <= current_index < len(questions):
            raw_question = questions[current_index]
            question = self._public_question(
                raw_question,
                current_index,
                session.get("answers", []),
                quiz.get("quiz_type"),
            )

        server_now = _utc_now()
        time_limit_minutes = int(quiz["time_limit_minutes"])
        duration_seconds = session.get("duration_seconds") or time_limit_minutes * 60
        started_at = _as_utc(session["started_at"])
        expires_at = _as_utc(session["expires_at"])
        submitted_at = (
            _as_utc(session["submitted_at"]) if session.get("submitted_at") else None
        )

        return {
            "session_id": str(session["_id"]),
            "quiz_id": session["quiz_id"],
            "title": quiz.get("title", "Live Quiz"),
            "participant_name": session["participant_name"],
            "participant_email": session.get("participant_email"),
            "started_at": started_at,
            "expires_at": expires_at,
            "server_now": server_now,
            "submitted_at": submitted_at,
            "status": "active"
            if session["status"] in {"joined", "disconnected"}
            else session["status"],
            "current_question_index": current_index,
            "total_questions": session["total_questions"],
            "time_limit_minutes": time_limit_minutes,
            "duration_seconds": duration_seconds,
            "duration_used_seconds": session.get("duration_used_seconds"),
            "remaining_seconds": self._remaining_seconds(expires_at, server_now),
            "question": question,
            "answers": session.get("answers", []),
            "score": session.get("score"),
            "percentage": session.get("percentage"),
            "auto_submitted": session.get("auto_submitted", False),
        }

    def _public_question(
        self,
        question: Dict[str, Any],
        index: int,
        answers: List[Dict[str, Any]],
        quiz_type: Optional[str],
    ) -> Dict[str, Any]:
        selected_answer = None
        for answer in answers:
            if answer.get("question_index") == index:
                selected_answer = answer.get("selected_answer")
                break
        return {
            "question_index": index,
            "question": question.get("question", ""),
            "options": question.get("options"),
            "question_type": question.get("question_type") or quiz_type,
            "selected_answer": selected_answer,
        }

    def _submission_response(
        self,
        session: Dict[str, Any],
        already_submitted: bool = False,
    ) -> Dict[str, Any]:
        return {
            "status": "already_submitted" if already_submitted else "submitted",
            "score": session["score"],
            "total_questions": session["total_questions"],
            "percentage": session["percentage"],
            "submitted_at": _as_utc(session["submitted_at"]),
            "auto_submitted": session.get("auto_submitted", False),
            "duration_used_seconds": session.get("duration_used_seconds"),
        }

    def _analytics_row(self, session: Dict[str, Any]) -> Dict[str, Any]:
        duration_seconds = session.get("duration_used_seconds")
        if session.get("submitted_at") and session.get("started_at"):
            duration_seconds = int(
                (_as_utc(session["submitted_at"]) - _as_utc(session["started_at"])).total_seconds()
            )
        total_questions = session.get("total_questions", 0)
        answered_count = len(session.get("answers", []))
        status = session.get("status", "active")
        if status == "active":
            status = "in_progress"
        if session.get("auto_submitted"):
            status = "timed_out"
        current_question_index = session.get("current_question_index", 0)
        current_question_number = (
            min(current_question_index + 1, total_questions) if total_questions else None
        )
        progress_percentage = (
            round((answered_count / total_questions) * 100, 2)
            if total_questions
            else 0
        )
        return {
            "session_id": str(session["_id"]),
            "participant_name": session.get("participant_name", ""),
            "participant_email": session.get("participant_email"),
            "score": session.get("score"),
            "total_questions": total_questions,
            "percentage": session.get("percentage"),
            "joined_at": session.get("joined_at") or session.get("started_at"),
            "started_at": session.get("started_at"),
            "submitted_at": session.get("submitted_at"),
            "duration_seconds": duration_seconds,
            "progress": answered_count,
            "current_question_number": current_question_number,
            "progress_percentage": progress_percentage,
            "status": status,
            "auto_submitted": session.get("auto_submitted", False),
        }

    def _quiz_status(
        self,
        quiz: Dict[str, Any],
        sessions: List[Dict[str, Any]],
    ) -> str:
        if any(session.get("status") in {"joined", "active"} for session in sessions):
            return "in_progress"
        expires_at = quiz.get("access_code_expires_at")
        if expires_at and _as_utc(expires_at) <= _utc_now():
            return "expired"
        if sessions and all(session.get("submitted_at") for session in sessions):
            return "completed"
        return "active"

    def _normalize_invited_emails(self, emails: List[str]) -> List[str]:
        adapter = TypeAdapter(EmailStr)
        normalized: list[str] = []
        invalid: list[str] = []
        for raw_email in emails:
            email = raw_email.strip().lower()
            if not email:
                continue
            try:
                adapter.validate_python(email)
            except ValidationError:
                invalid.append(raw_email)
                continue
            if email not in normalized:
                normalized.append(email)
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid invitation email(s): {', '.join(invalid)}",
            )
        return normalized

    def _join_link(self, access_code: str, frontend_origin: Optional[str]) -> str:
        origin = (frontend_origin or "").rstrip("/")
        if not origin:
            return f"/quiz-access/{access_code}"
        return f"{origin}/quiz-access/{access_code}"

    def _invitation_email_body(
        self,
        *,
        title: str,
        access_code: str,
        join_link: str,
        starts_at: Optional[datetime],
        ends_at: datetime,
        time_limit_minutes: int,
    ) -> str:
        start_text = starts_at.isoformat() if starts_at else "Available now"
        return (
            f"You have been invited to take this live quiz: {title}\n\n"
            f"Access code: {access_code}\n"
            f"Join link: {join_link}\n"
            f"Start: {start_text}\n"
            f"Access code expires: {ends_at.isoformat()}\n"
            f"Quiz duration: {time_limit_minutes} minutes\n"
        )

    async def _publish_participant_event(
        self,
        quiz_id: str,
        session_id: str,
        event_type: str,
    ) -> None:
        if not self.broadcaster:
            return
        session = await self.repository.get_session(session_id)
        if not session:
            return
        await self.broadcaster.publish(
            quiz_id,
            {
                "type": event_type,
                "quiz_id": quiz_id,
                "participant": self._analytics_row(session),
            },
        )

    def _is_expired(self, session: Dict[str, Any]) -> bool:
        return _as_utc(session["expires_at"]) <= _utc_now()

    def _remaining_seconds(
        self,
        expires_at: datetime,
        server_now: Optional[datetime] = None,
    ) -> int:
        now = _as_utc(server_now) if server_now else _utc_now()
        return max(0, int((_as_utc(expires_at) - now).total_seconds()))
