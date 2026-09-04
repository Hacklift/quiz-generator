import csv
from datetime import datetime, timezone
from io import StringIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pypdf import PdfReader

from server.app.quiz.routes.live_sessions import export_live_quiz_results
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.utils.live_results_export import (
    generate_live_results_csv,
    generate_live_results_pdf,
    generate_live_results_txt,
)


class ResultsRepository:
    def __init__(self, *, owner_id="teacher-1", sessions=None):
        self.quiz = {
            "_id": "quiz-1",
            "title": "Commas, Quotes & Lines",
            "owner_user_id": owner_id,
            "quiz_type": "multichoice",
            "questions": [
                {"question": "Q1", "answer": "A"},
                {"question": "Q2", "answer": "B"},
                {"question": "Q3", "answer": "C"},
            ],
        }
        self.sessions = sessions or []

    async def get_quiz_by_id(self, quiz_id):
        return self.quiz if quiz_id == "quiz-1" else None

    async def list_quiz_sessions(self, quiz_id):
        return self.sessions


def completed_participant(name, results, score, percentage):
    return {
        "_id": f"attempt-{name}",
        "quiz_id": "quiz-1",
        "creator_user_id": "teacher-1",
        "participant_name": name,
        "status": "submitted",
        "submitted_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "score": score,
        "percentage": percentage,
        "graded_answers": results,
        # Values resembling hostile browser input are unrelated to export data.
        "client_supplied_score": 100,
        "client_supplied_percentage": 100,
    }


@pytest.mark.asyncio
async def test_owner_export_uses_persisted_server_grades_for_multiple_participants():
    sessions = [
        completed_participant(
            'Alice, "A"\nStudent',
            [
                {"question_index": 0, "selected_answer": "A", "is_correct": True},
                {"question_index": 1, "selected_answer": "A", "is_correct": False},
            ],
            1,
            33.33,
        ),
        completed_participant(
            "Bob",
            [
                {"question_index": 0, "selected_answer": "B", "is_correct": False},
                {"question_index": 1, "selected_answer": "B", "is_correct": True},
                {"question_index": 2, "selected_answer": "C", "is_correct": True},
            ],
            2,
            66.67,
        ),
    ]
    payload = await LiveQuizSessionService(
        ResultsRepository(sessions=sessions)
    ).build_results_export("quiz-1", "teacher-1")
    rows = list(csv.reader(StringIO(generate_live_results_csv(payload).getvalue())))

    assert rows[0] == ["Participant", "Q1", "Q2", "Q3", "Score", "Percentage"]
    assert rows[1] == [
        'Alice, "A"\nStudent',
        "Correct",
        "Incorrect",
        "Unanswered",
        "1/3",
        "33.33%",
    ]
    assert rows[2] == ["Bob", "Incorrect", "Correct", "Correct", "2/3", "66.67%"]
    assert "100" not in rows[1]


@pytest.mark.asyncio
async def test_export_only_includes_fully_submitted_sessions():
    completed = completed_participant(
        "Completed",
        [{"question_index": 0, "selected_answer": "A", "is_correct": True}],
        1,
        33.33,
    )
    active_with_timestamp = {
        **completed_participant("Active with timestamp", [], 0, 0),
        "status": "active",
    }
    submitted_without_timestamp = {
        **completed_participant("Submitted without timestamp", [], 0, 0),
        "submitted_at": None,
    }
    active = {
        **completed_participant("Active", [], 0, 0),
        "status": "active",
        "submitted_at": None,
    }

    payload = await LiveQuizSessionService(
        ResultsRepository(
            sessions=[
                completed,
                active_with_timestamp,
                submitted_without_timestamp,
                active,
            ]
        )
    ).build_results_export("quiz-1", "teacher-1")

    assert [row["participant_name"] for row in payload["participants"]] == [
        "Completed"
    ]


@pytest.mark.asyncio
async def test_export_preserves_historical_session_question_count():
    session = completed_participant(
        "Historical Participant",
        [
            {"question_index": 0, "selected_answer": "A", "is_correct": True},
            {"question_index": 1, "selected_answer": "B", "is_correct": True},
            {"question_index": 2, "selected_answer": "A", "is_correct": False},
        ],
        2,
        66.67,
    )
    session["total_questions"] = 3
    repository = ResultsRepository(sessions=[session])
    repository.quiz["questions"].append({"question": "Q4", "answer": "D"})

    payload = await LiveQuizSessionService(repository).build_results_export(
        "quiz-1", "teacher-1"
    )
    csv_text = generate_live_results_csv(payload).getvalue()

    assert payload["participants"][0]["total_questions"] == 3
    assert payload["participants"][0]["percentage"] == 66.67
    assert "2/3,66.67%" in csv_text
    assert "2/4" not in csv_text


@pytest.mark.asyncio
async def test_ownerless_or_other_owner_cannot_export_results():
    service = LiveQuizSessionService(ResultsRepository(owner_id="teacher-1"))
    with pytest.raises(HTTPException) as error:
        await service.build_results_export("quiz-1", "teacher-2")
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_authenticated_creator_route_exports_csv():
    payload = {"title": "Class Results", "question_count": 0, "participants": []}

    class Service:
        async def build_results_export(self, quiz_id, requester_id):
            assert (quiz_id, requester_id) == ("quiz-1", "teacher-1")
            return payload

    response = await export_live_quiz_results(
        "quiz-1",
        "csv",
        SimpleNamespace(id="teacher-1", persona_user_type="teacher"),
        Service(),
    )
    chunks = [chunk async for chunk in response.body_iterator]
    body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in chunks)
    assert body == "Participant,Score,Percentage\n"
    assert response.media_type == "text/csv"
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="Class Results results.csv"'

def test_empty_text_and_pdf_exports_are_valid():
    payload = {"title": "Empty Results", "question_count": 2, "participants": []}
    assert "No completed participants." in generate_live_results_txt(payload).getvalue()
    reader = PdfReader(generate_live_results_pdf(payload))
    assert "No completed participants." in "".join(page.extract_text() for page in reader.pages)
