import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from server.app.quiz.routers.quiz import router as quiz_router
from server.app.auth.dependencies import get_current_user_optional

app = FastAPI()
app.include_router(quiz_router, prefix="/api")
app.dependency_overrides[get_current_user_optional] = lambda: None

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_hf_down(monkeypatch):
    async def _raise(*args, **kwargs):
        raise Exception("mocked HF down")

    monkeypatch.setattr(
        "server.app.quiz.utils.questions.generate_quiz_with_huggingface",
        _raise,
    )

def build_payload(question_type: str, num_questions: int):
    return {
        "profession": "Engineer",
        "num_questions": num_questions,
        "question_type": question_type,
        "difficulty_level": "medium",
        "audience_type": "students",
        "custom_instruction": "",
    }

def test_get_questions_multichoice_success():
    payload = build_payload("multichoice", 3)
    response = client.post("/api/get-questions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) == 3
    for question in data["questions"]:
        assert "question" in question
        assert "options" in question
        assert "question_type" in question
        assert "answer" in question

def test_get_questions_true_false_success():
    payload = build_payload("true-false", 5)
    response = client.post("/api/get-questions", json=payload)
    assert response.status_code == 200
    data = response.json()
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

def test_get_questions_open_ended_success():
    payload = build_payload("open-ended", 3)
    response = client.post("/api/get-questions", json=payload)
    assert response.status_code == 200
    data = response.json()
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

def test_get_questions_invalid_type():
    payload = build_payload("invalid-type", 2)
    response = client.post("/api/get-questions", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "No mock data for question type" in data["detail"]

def test_get_questions_exceeding_available():
    payload = build_payload("multichoice", 20)
    response = client.post("/api/get-questions", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "Requested" in data["detail"]

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
    response = client.post("/api/grade-answers", json=payload)
    assert response.status_code == 200
    data = response.json()
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
    response = client.post("/api/grade-answers", json=payload)
    assert response.status_code == 200
    data = response.json()
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
    response = client.post("/api/grade-answers", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "accuracy_percentage" in data[0]
    assert "result" in data[0]
    assert data[0]["is_correct"] in [True, False]  

def test_generate_quiz():
    payload = build_payload("multichoice", 3)
    response = client.post("/api/get-questions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "source" in data
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) == 3
