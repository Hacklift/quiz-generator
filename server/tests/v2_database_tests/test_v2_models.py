import pytest
from pydantic import ValidationError

from ...app.db.v2.models.quiz_models import QuizCreateV2, QuizMetadataUpdateV2, QuizQuestionV2


def test_quiz_create_v2_accepts_valid_payload():
    payload = QuizCreateV2(
        title="Backend Fundamentals",
        description="Core backend quiz",
        quiz_type="multichoice",
        source="manual",
        questions=[
            {
                "question": "What does HTTP stand for?",
                "options": ["HyperText Transfer Protocol", "High Transfer Text Process"],
                "correct_answer": "HyperText Transfer Protocol",
            }
        ],
    )

    assert payload.title == "Backend Fundamentals"
    assert payload.questions[0].correct_answer == "HyperText Transfer Protocol"


def test_quiz_question_v2_normalizes_legacy_answer_field():
    question = QuizQuestionV2(
        question="The sky is blue.",
        options=["True", "False"],
        answer="True",
    )

    assert question.correct_answer == "True"


def test_quiz_create_v2_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        QuizCreateV2(quiz_type="multichoice", questions=[])


def test_quiz_create_v2_rejects_invalid_quiz_type():
    with pytest.raises(ValidationError):
        QuizCreateV2(
            title="Invalid",
            quiz_type="multiple_choice",
            questions=[
                {
                    "question": "Bad type",
                    "correct_answer": "x",
                }
            ],
        )


def test_quiz_metadata_update_v2_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        QuizMetadataUpdateV2(title="Valid", unknown_field="nope")
