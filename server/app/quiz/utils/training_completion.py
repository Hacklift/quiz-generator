"""Shared completion evidence for HTTP and worker-owned run closure."""

import csv
import io
import math
from copy import deepcopy
from datetime import datetime, timezone


# Interactive reports are synchronous. Closure evidence has no row truncation.
MAX_COMPLETION_REPORT_ROWS = 10_000


def report_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
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
        "recipient_email": assignment["recipient_email"],
        "recipient_name": assignment.get("recipient_name"),
        "recipient_user_id": assignment.get("recipient_user_id"),
        "status": assignment["status"],
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
    shared = "session_id" in record
    state = record["status"]
    if shared:
        state = "completed" if state == "submitted" else "incomplete" if state == "abandoned" else "in_progress"
    percentage = record.get("percentage" if shared else "latest_percentage")
    return {
        "assignment_id": record["session_id"] if shared else record["assignment_id"],
        "recipient_email": record.get("participant_email" if shared else "recipient_email"),
        "recipient_name": record.get("participant_name" if shared else "recipient_name"),
        "participant_type": "shared_link" if shared else "assigned",
        "status": state,
        "due_at": report_timestamp(record.get("due_at")),
        "attempts_used": 1 if shared else record.get("attempts_used", 0),
        "max_attempts": None if shared else record.get("max_attempts"),
        "started_at": report_timestamp(record.get("started_at")),
        "completed_at": report_timestamp(record.get("submitted_at" if shared else "completed_at")),
        "latest_score": record.get("score" if shared else "latest_score"),
        "latest_percentage": percentage,
        "outcome": record.get("outcome") or completion_outcome(state, percentage, threshold),
    }


def build_closure_payload(run: dict, assignments: list[dict], sessions: list[dict]) -> dict:
    threshold = run.get("passing_threshold_percentage")
    records = [
        *[assignment_snapshot(item) for item in assignments],
        *[shared_session_snapshot(item) for item in sessions if not item.get("training_assignment_id")],
    ]
    for record in records:
        record["outcome"] = completion_row(record, threshold)["outcome"]
    return deepcopy({
        "report_schema_version": 1,
        "run": {key: run.get(key) for key in (
            "quiz_id", "title", "kind", "purpose", "access_mode", "time_limit_minutes",
            "due_at", "closes_at", "quiz_content_fingerprint", "quiz_snapshot",
            "passing_threshold_percentage",
        )},
        "completion_register": records,
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
