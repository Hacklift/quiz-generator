from fastapi import HTTPException

from .mock_grading import grade_mock_answers

from .ai_grading import grade_with_ai


def grade_answers(user_answers: list, source: str = "mock"):

    """
    Grade answers from either a mock quiz or an AI-generated quiz.

    :param user_answers: list of dicts containing answers
    :param source: "mock" or "ai"
    :return: list of graded answer dicts
    """

    if source == "mock":

        return grade_mock_answers(user_answers)

    elif source == "ai":

        return grade_with_ai(user_answers)

    else:

        raise HTTPException(status_code=400, detail="Invalid quiz source. Must be 'mock' or 'ai'.")

