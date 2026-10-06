import pytest
from pydantic import ValidationError

from ...app.quiz.repositories.v2.models.quiz_models import QuizCreateV2, QuizMetadataUpdateV2, QuizQuestionV2
from ...app.quiz.repositories.v2.models.attempt_models import QuizAttemptDocumentV2


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


def test_quiz_create_v2_accepts_optional_category_metadata():
    payload = QuizCreateV2(
        title="Biology Basics",
        quiz_type="short-answer",
        source="seed",
        visibility="public",
        category="Science",
        category_slug="science",
        subcategory="Biology",
        subcategory_slug="biology",
        tags=["science", "biology", "short-answer"],
        classification={"method": "seed_path", "confidence": 1.0},
        questions=[
            {
                "question": "What is the basic unit of life?",
                "correct_answer": "Cell",
            }
        ],
    )

    assert payload.quiz_type == "short-answer"
    assert payload.category_slug == "science"
    assert payload.classification.method == "seed_path"


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


def test_matching_quiz_uses_structured_authoritative_answer():
    quiz = QuizCreateV2(
        title="Matching", quiz_type="matching", source="manual",
        questions=[{"question": "Match", "options": ["Paris"], "correct_answer": {"France": "Paris"}}],
    )
    assert quiz.questions[0].correct_answer == {"France": "Paris"}


def test_attempt_rejects_inconsistent_authoritative_aggregate():
    with pytest.raises(ValidationError):
        QuizAttemptDocumentV2(
            user_id="learner", quiz_id="quiz", score=1, total_questions=2, percentage=100,
            question_results=[
                {"question_index": 0, "question": "Q1", "question_type": "multichoice",
                 "user_answer": "A", "correct_answer": "A", "is_correct": True, "result": "Correct"},
                {"question_index": 1, "question": "Q2", "question_type": "multichoice",
                 "user_answer": "A", "correct_answer": "B", "is_correct": False, "result": "Incorrect"},
            ],
        )
