"""Percentage-based recipient statistics, retained with closure evidence."""

import math


def has_completed(record):
    return record.get("status") == "completed" or record.get("completed_at") is not None


def recipient_statistics(records):
    participant_count = completed_count = scored = 0
    total = 0.0
    for record in records:
        participant_count += 1
        if not has_completed(record):
            continue
        completed_count += 1
        value = record.get("latest_percentage")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 100:
            scored += 1
            total += value
    return {
        "participant_count": participant_count,
        "completed_count": completed_count,
        "outstanding_count": participant_count - completed_count,
        "completion_percentage": round(completed_count * 100 / participant_count, 2) if participant_count else 0.0,
        "average_percentage": round(total / scored, 2) if scored else None,
    }


def add_assignment_closure_evidence(payload, run, assignments):
    if run.get("delivery_kind") == "quiz":
        payload["completion_register"].sort(key=lambda row: row.get("assignment_id", ""), reverse=True)
        payload["assignment_summary"] = (
            None if any(row.get("interpretation_error") for row in payload["completion_register"])
            else recipient_statistics(assignments)
        )
        payload["run"].update({key: run.get(key) for key in (
            "quiz_revision_id", "delivery_kind", "cohort_id", "available_from",
        )})
    return payload
