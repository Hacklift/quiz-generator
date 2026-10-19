"""Shared completion evidence for HTTP and worker-owned run closure."""

import csv
import io
import logging
import math
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime, timezone


# Interactive reports are synchronous. Closure evidence has no row truncation.
MAX_COMPLETION_REPORT_ROWS = 10_000
STARTED_ASSIGNMENT_STATUSES = ("in_progress", "submitting", "incomplete", "completed")
COMPLETION_OUTCOMES = ("passed", "failed", "not_completed", "unknown")
SHARED_SESSION_STATES = {
    "submitted": "completed", "abandoned": "incomplete", "expired": "incomplete",
    "active": "in_progress", "joined": "in_progress", "disconnected": "in_progress",
    "closing": "in_progress",
}
REPORT_METADATA_FIELDS = (
    "quiz_id", "title", "kind", "purpose", "access_mode", "time_limit_minutes",
    "due_at", "closes_at", "passing_threshold_percentage",
)
logger = logging.getLogger(__name__)


class CompletionEvidenceError(ValueError):
    """Stored completion evidence cannot be interpreted safely."""


def closed_run_metadata(run: dict, snapshot: dict) -> dict:
    # Optional nulls are evidence (e.g. no due date). Required nulls in older
    # snapshots are omissions, not overrides of the immutable run configuration.
    merged = dict(run)
    for key in REPORT_METADATA_FIELDS:
        if key in snapshot and (snapshot[key] is not None or key in ("due_at", "passing_threshold_percentage")):
            merged[key] = snapshot[key]
    # Never invent a historical passing threshold from the current run document.
    merged["passing_threshold_percentage"] = snapshot.get("passing_threshold_percentage")
    return merged


def raw_score(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0 or (isinstance(value, float) and (not math.isfinite(value) or not value.is_integer())):
        return None
    return int(value)


def completion_summary(rows: Iterable[dict]) -> dict:
    counts = {key: 0 for key in ("participant_count", "assigned_count", "started_count", "completed_count")}
    score_sum = score_count = 0
    for row in rows:
        counts["participant_count"] += 1
        counts["assigned_count"] += row["participant_type"] == "assigned"
        counts["started_count"] += row["participant_type"] == "shared_link" or row["status"] in STARTED_ASSIGNMENT_STATUSES
        if row["status"] == "completed":
            counts["completed_count"] += 1
            score = raw_score(row.get("latest_score"))
            if score is not None:
                score_sum += score
                score_count += 1
    return {**counts, "average_score": round(score_sum / score_count, 2) if score_count else None}


def report_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise CompletionEvidenceError("Invalid evidence timestamp")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def completion_outcome(status: str, percentage, threshold) -> str:
    if status != "completed":
        return "not_completed"
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not math.isfinite(value) or not 0 <= value <= 100
        for value in (percentage, threshold)
    ):
        return "unknown"
    return "passed" if percentage >= threshold else "failed"


def assignment_snapshot(assignment: dict) -> dict:
    return {
        "assignment_id": str(assignment["_id"]),
        "recipient_email": assignment.get("recipient_email"),
        "recipient_name": assignment.get("recipient_name"),
        "recipient_user_id": assignment.get("recipient_user_id"),
        "status": assignment.get("status"),
        "attempts_used": assignment.get("attempts_used", 0),
        "max_attempts": assignment.get("max_attempts"),
        "due_at": assignment.get("due_at"),
        "started_at": assignment.get("started_at"),
        "completed_at": assignment.get("completed_at"),
        "latest_score": assignment.get("latest_score"),
        "latest_percentage": assignment.get("latest_percentage"),
    }


def shared_session_snapshot(session: dict) -> dict:
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


def completion_row(record: dict, threshold) -> dict:
    if not isinstance(record, dict):
        raise CompletionEvidenceError("Invalid completion record")
    if record.get("interpretation_error"):
        raise CompletionEvidenceError("Uninterpretable retained completion record")
    shared = "session_id" in record
    identifier = record.get("session_id" if shared else "assignment_id")
    if not isinstance(identifier, str) or not identifier:
        raise CompletionEvidenceError("Missing completion record identifier")
    state = record.get("status")
    if shared:
        if not isinstance(state, str) or state not in SHARED_SESSION_STATES:
            raise CompletionEvidenceError("Invalid shared-session state")
        state = SHARED_SESSION_STATES[state]
    elif state == "submitting":
        state = "in_progress"
    elif not isinstance(state, str) or state not in ("assigned", *STARTED_ASSIGNMENT_STATUSES):
        raise CompletionEvidenceError("Invalid assignment state")
    percentage = record.get("percentage" if shared else "latest_percentage")
    outcome = record.get("outcome")
    if outcome is not None and (not isinstance(outcome, str) or outcome not in COMPLETION_OUTCOMES):
        raise CompletionEvidenceError("Invalid stored completion outcome")
    return {
        "assignment_id": identifier,
        "recipient_email": record.get("participant_email" if shared else "recipient_email"),
        "recipient_name": record.get("participant_name" if shared else "recipient_name"),
        "participant_type": "shared_link" if shared else "assigned",
        "status": state,
        "due_at": report_timestamp(record.get("due_at")),
        "attempts_used": 1 if shared else record.get("attempts_used", 0),
        "max_attempts": None if shared else record.get("max_attempts"),
        "started_at": report_timestamp(record.get("started_at")),
        "completed_at": report_timestamp(record.get("submitted_at" if shared else "completed_at")),
        "latest_score": raw_score(record.get("score" if shared else "latest_score")),
        "latest_percentage": percentage,
        "outcome": outcome if outcome is not None else completion_outcome(state, percentage, threshold),
    }


def build_closure_payload(run: dict, assignments: list[dict], sessions: list[dict]) -> dict:
    threshold = run.get("passing_threshold_percentage")
    records = [
        *[assignment_snapshot(item) for item in assignments],
        *[shared_session_snapshot(item) for item in sessions if not item.get("training_assignment_id")],
    ]
    unknown_records = 0
    for record in records:
        try:
            record["outcome"] = completion_row(record, threshold)["outcome"]
        except CompletionEvidenceError:
            # Capture must not depend on our ability to interpret legacy/new
            # states. Preserve the raw values; strict readers remain fail-closed.
            record["outcome"] = "unknown"
            record["interpretation_error"] = True
            unknown_records += 1
    if unknown_records:
        logger.warning(
            "training_closure_uninterpretable_records run_id=%s count=%s", run.get("_id"), unknown_records,
        )
    return deepcopy({
        "report_schema_version": 2,
        "run": {key: run.get(key) for key in (
            "quiz_id", "title", "kind", "purpose", "access_mode", "time_limit_minutes",
            "due_at", "closes_at", "quiz_content_fingerprint", "quiz_snapshot",
            "passing_threshold_percentage",
        ) if key in run},
        "completion_register": records,
        # Captured atomically with the register. None deliberately marks
        # uninterpretable evidence; readers must not synthesize final counters.
        "summary": None if unknown_records else completion_summary(
            completion_row(record, threshold) for record in records
        ),
    })


def _csv_text(value) -> str:
    text = "" if value is None else str(value)
    # CSV quoting handles separators/newlines; a text prefix prevents formula
    # interpretation of untrusted names/titles in common spreadsheet viewers.
    if text.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠")) or text.startswith(("\t", "\r", "\n", "\ufeff")):
        return "'" + text
    return text


def _utc_timestamp(value: datetime | None) -> str:
    value = report_timestamp(value)
    return value.isoformat() if value is not None else ""


def completion_report_csv(report: dict, *, generated_at: datetime) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([
        "run_id", "quiz_id", "title", "record_status", "finalized_at_utc",
        "passing_threshold_percentage", "assignee_email", "assignee_name", "participant_type",
        "completion_status", "completed_at_utc", "score", "percentage", "outcome",
        "attempts_used", "max_attempts", "generated_at_utc",
    ])
    for row in report["completion_register"]:
        values = [
            report["id"], report["quiz_id"], report["title"],
            "final" if report["report_is_final"] else "provisional",
            _utc_timestamp(report.get("report_finalized_at")), report.get("passing_threshold_percentage"),
            row.get("recipient_email"), row.get("recipient_name"),
            row["participant_type"], "not_started" if row["status"] == "assigned" else row["status"],
            _utc_timestamp(row.get("completed_at")), row.get("latest_score"), row.get("latest_percentage"),
            row["outcome"], row["attempts_used"], row.get("max_attempts"), _utc_timestamp(generated_at),
        ]
        writer.writerow([_csv_text(value) if isinstance(value, str) else value for value in values])
    return buffer.getvalue()
