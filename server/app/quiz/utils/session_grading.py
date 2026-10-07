from typing import Any

from server.app.quiz.services.quiz_grading_service import QuizGradingService


def grade_live_session(session: dict[str, Any], quiz: dict[str, Any]) -> dict[str, Any]:
    """Grade a stored live session from its immutable quiz content."""
    questions = quiz.get("questions") or []
    answer_by_index = {
        answer["question_index"]: answer.get("selected_answer", "")
        for answer in session.get("answers", [])
    }
    canonical_questions = []
    submitted_answers = []
    for index, question in enumerate(questions):
        canonical_questions.append(
            {
                "question": question.get("question", ""),
                "correct_answer": question.get("correct_answer") or question.get("answer"),
                "question_type": question.get("question_type")
                or quiz.get("quiz_type")
                or "multichoice",
            }
        )
        submitted_answers.append(
            {"question_index": index, "user_answer": answer_by_index.get(index, "")}
        )

    grading = QuizGradingService.grade_canonical_questions(
        canonical_questions,
        submitted_answers,
        quiz_type=quiz.get("quiz_type") or "multichoice",
    )
    graded_answers = grading["question_results"]
    indexed_answers = [
        {
            "question_index": answer["question_index"],
            "question": answer.get("question", ""),
            "selected_answer": answer.get("user_answer", ""),
            "correct_answer": answer.get("correct_answer", ""),
            "question_type": answer.get("question_type", ""),
            "is_correct": bool(answer.get("is_correct", False)),
        }
        for answer in graded_answers
    ]
    return {
        "score": grading["score"],
        "percentage": grading["percentage"],
        "graded_answers": indexed_answers,
    }
