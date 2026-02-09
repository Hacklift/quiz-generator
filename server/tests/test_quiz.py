import pytest

from fastapi import HTTPException

from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.questions import get_questions
from server.app.quiz.utils.grading import grade_answers


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

    req = build_request("multichoice", 3)

    data = await get_questions(req, user_id=None)

    assert isinstance(data, dict)

    assert isinstance(data["questions"], list)

    assert len(data["questions"]) == 3

    for question in data["questions"]:

        assert "question" in question

        assert "options" in question

        assert "question_type" in question

        assert "answer" in question

@pytest.mark.asyncio
async def test_get_questions_true_false_success():

    req = build_request("true-false", 5)

    data = await get_questions(req, user_id=None)

    assert isinstance(data, dict)

    assert isinstance(data["questions"], list)

    assert len(data["questions"]) == 5

    for question in data["questions"]:

        assert "question" in question

        assert "options" in question

        assert isinstance(question["options"], list)

        assert "question_type" in question

        assert question["question_type"] == "true-false"

        assert "answer" in question

@pytest.mark.asyncio
async def test_get_questions_open_ended_success():

    req = build_request("open-ended", 3)

    data = await get_questions(req, user_id=None)

    assert isinstance(data, dict)

    assert isinstance(data["questions"], list)

    assert len(data["questions"]) == 3

    for question in data["questions"]:

        assert "question" in question

        if "options" in question:

            assert question["options"] == [] or question["options"] is None

        assert "question_type" in question

        assert question["question_type"] == "open-ended"

        assert "answer" in question

        assert question["answer"] != ""

@pytest.mark.asyncio
async def test_get_questions_invalid_type():

    req = build_request("invalid-type", 2)

    with pytest.raises(HTTPException) as exc:
        await get_questions(req, user_id=None)

    assert exc.value.status_code == 400
    assert "No mock data for question type" in exc.value.detail

@pytest.mark.asyncio
async def test_get_questions_exceeding_available():

    req = build_request("multichoice", 20)

    with pytest.raises(HTTPException) as exc:
        await get_questions(req, user_id=None)

    assert exc.value.status_code == 400
    assert "Requested" in exc.value.detail


def test_grade_answers_multichoice():

    payload = [

        {

            "question": "What is the capital of France?",

            "user_answer": "Paris",

            "correct_answer": "Paris",

            "question_type": "multichoice"

        },

        {

            "question": "Which planet is known as the Red Planet?",

            "user_answer": "Jupiter",

            "correct_answer": "Mars",

            "question_type": "multichoice"

        },

    ]

    data = grade_answers(payload, source="mock")

    assert isinstance(data, list)

    assert len(data) == 2

    assert data[0]["is_correct"] is True

    assert data[0]["result"] == "Correct"

    assert data[1]["is_correct"] is False

    assert data[1]["result"] == "Incorrect"


def test_grade_answers_true_false():

    payload = [

        {

            "question": "The Earth is flat.",

            "user_answer": "false",

            "correct_answer": "false",

            "question_type": "true-false"

        },

        {

            "question": "Water boils at 100°C.",

            "user_answer": "true",

            "correct_answer": "true",

            "question_type": "true-false"

        },

        {

            "question": "The sun revolves around the Earth.",

            "user_answer": "false",

            "correct_answer": "false",

            "question_type": "true-false"

        },

    ]

    data = grade_answers(payload, source="mock")

    assert isinstance(data, list)

    assert len(data) == 3

    for item in data:

        if item["question"] == "Water boils at 100°C.":

            assert item["is_correct"] is True

            assert item["result"] == "Correct"

        else:

            assert item["is_correct"] is True

            assert item["result"] == "Correct"


def test_grade_answers_open_ended():

    payload = [

        {

            "question": "Explain the process of photosynthesis.",

            "user_answer": "Photosynthesis uses sunlight to make food from carbon dioxide and water.",

            "correct_answer": (

                "Photosynthesis is the process by which green plants and some organisms use sunlight to synthesize foods with the help of chlorophyll. "

                "It involves the conversion of carbon dioxide and water into glucose and oxygen."

            ),

            "question_type": "open-ended"

        }

    ]

    data = grade_answers(payload, source="mock")

    assert "accuracy_percentage" in data[0]

    assert "result" in data[0]

    assert data[0]["is_correct"] in [True, False]


@pytest.mark.asyncio
async def test_generate_quiz():

    req = build_request("multichoice", 3)

    data = await get_questions(req, user_id=None)

    assert "source" in data

    assert isinstance(data["questions"], list)

    assert len(data["questions"]) == 3
