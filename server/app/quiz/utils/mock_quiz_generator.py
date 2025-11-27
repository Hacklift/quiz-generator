from server.app.quiz.mock_data.multi_choice import mock_multiple_choice_questions
from server.app.quiz.mock_data.true_false import mock_true_false_questions
from server.app.quiz.mock_data.open_ended import mock_open_ended_questions
from server.app.quiz.mock_data.short_answer import mock_short_answer_questions

from fastapi import HTTPException
import random


def get_mock_questions_by_type(question_type: str, num_questions: int):
    normalized_map = {
        "multiple choice": "multichoice",
        "multichoice": "multichoice",
        "true or false": "true-false",
        "true-false": "true-false",
        "open ended": "open-ended",
        "open-ended": "open-ended",
        "short answers": "short-answer",
        "short answer": "short-answer",
        "short-answer": "short-answer"
    }

    mock_dispatch = {
        "multichoice": mock_multiple_choice_questions,
        "true-false": mock_true_false_questions,
        "open-ended": mock_open_ended_questions,
        "short-answer": mock_short_answer_questions,
    }

    normalized_key = normalized_map.get(question_type.strip().lower())

    if not normalized_key or normalized_key not in mock_dispatch:
        raise HTTPException(
            status_code=400, 
            detail=f"No mock data for question type: {question_type}"
        )

    questions = mock_dispatch[normalized_key]

    if callable(questions):
        questions = questions()  

    if num_questions > len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Requested {num_questions} questions, but only {len(questions)} available."
        )

    return random.sample(questions, num_questions)
