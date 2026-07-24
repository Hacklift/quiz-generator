import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException, Response

from server.app.quiz.models.quiz_models import QuizRequest
from server.app.core.rate_limiter import limiter
from server.app.quiz.routes.generation import get_quiz
from server.app.quiz.services.quiz_grading_service import (
    SubmissionMismatchError,
    grade_against_stored_questions,
)


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    original_enabled = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original_enabled


@pytest.fixture(autouse=True)
def mock_hf_down(monkeypatch):
    async def _raise(*args, **kwargs):
        raise Exception("mocked HF down")

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        _raise,
    )


def build_request(question_type: str, num_questions: int) -> QuizRequest:
    return QuizRequest(
        profession="Engineer",
        num_questions=num_questions,
        question_type=question_type,
        difficulty_level="medium",
        audience_type="students",
        custom_instruction="",
    )


@pytest.mark.asyncio
async def test_get_questions_multichoice_success():
    data = await get_quiz(MagicMock(), Response(), build_request("multichoice", 3), current_user=None)

    assert isinstance(data["questions"], list)
    assert len(data["questions"]) == 3
    for question in data["questions"]:
        assert "question" in question
        assert "options" in question
        assert "question_type" in question
        assert "answer" in question


@pytest.mark.asyncio
async def test_get_questions_true_false_success():
    data = await get_quiz(MagicMock(), Response(), build_request("true-false", 5), current_user=None)

    assert len(data["questions"]) == 5
    for question in data["questions"]:
        assert isinstance(question["options"], list)
        assert question["question_type"] == "true-false"
        assert "answer" in question


@pytest.mark.asyncio
async def test_get_questions_open_ended_success():
    data = await get_quiz(MagicMock(), Response(), build_request("open-ended", 3), current_user=None)

    assert len(data["questions"]) == 3
    for question in data["questions"]:
        assert question.get("options") in ([], None)
        assert question["question_type"] == "open-ended"
        assert question["answer"] != ""


@pytest.mark.asyncio
async def test_get_questions_invalid_type():
    with pytest.raises(HTTPException) as exc:
        await get_quiz(MagicMock(), Response(), build_request("invalid-type", 2), current_user=None)

    assert exc.value.status_code == 400
    assert "No mock data for question type" in exc.value.detail


@pytest.mark.asyncio
async def test_get_questions_exceeding_available():
    with pytest.raises(HTTPException) as exc:
        await get_quiz(MagicMock(), Response(), build_request("multichoice", 20), current_user=None)

    assert exc.value.status_code == 422
    assert "limited to" in exc.value.detail


def test_grade_against_stored_questions_multichoice():
    stored = [
        {"question": "What is the capital of France?", "correct_answer": "Paris"},
        {"question": "Which planet is known as the Red Planet?", "correct_answer": "Mars"},
    ]
    submitted = [
        {"question": "What is the capital of France?", "user_answer": "Paris"},
        {"question": "Which planet is known as the Red Planet?", "user_answer": "Jupiter"},
    ]

    data = grade_against_stored_questions(stored, submitted, quiz_type="multichoice")

    assert len(data) == 2
    assert data[0]["is_correct"] is True
    assert data[0]["result"] == "Correct"
    assert data[1]["is_correct"] is False
    assert data[1]["result"] == "Incorrect"


def test_grade_against_stored_questions_true_false_normalizes_formats():
    stored = [
        {"question": "The Earth is flat.", "correct_answer": "False"},
        {"question": "Water boils at 100 C.", "correct_answer": "1"},
    ]
    submitted = [
        {"question": "The Earth is flat.", "user_answer": "false"},
        {"question": "Water boils at 100 C.", "user_answer": "true"},
    ]

    data = grade_against_stored_questions(stored, submitted, quiz_type="true-false")

    assert len(data) == 2
    assert all(item["is_correct"] is True for item in data)
    assert data[0]["correct_answer"] == "false"


def test_grade_against_stored_questions_open_ended():
    stored = [
        {
            "question": "Explain the process of photosynthesis.",
            "correct_answer": (
                "Photosynthesis is the process by which green plants and some organisms use "
                "sunlight to synthesize foods with the help of chlorophyll."
            ),
        }
    ]
    submitted = [
        {
            "question": "Explain the process of photosynthesis.",
            "user_answer": "Photosynthesis uses sunlight to make food from carbon dioxide and water.",
        }
    ]

    data = grade_against_stored_questions(stored, submitted, quiz_type="open-ended")

    assert "accuracy_percentage" in data[0]
    assert "result" in data[0]
    assert data[0]["is_correct"] in [True, False]


def test_grade_against_stored_questions_rejects_unknown_question():
    stored = [{"question": "Real question?", "correct_answer": "Yes"}]
    submitted = [{"question": "Injected question?", "user_answer": "Yes"}]

    with pytest.raises(SubmissionMismatchError):
        grade_against_stored_questions(stored, submitted, quiz_type="multichoice")

    assert "accuracy_percentage" in data[0]
    assert "result" in data[0]
    assert data[0]["is_correct"] in [True, False]


@pytest.mark.asyncio
async def test_generate_quiz():
    data = await get_quiz(MagicMock(), Response(), build_request("multichoice", 3), current_user=None)

    assert data["source"] == "mock"
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) == 3
