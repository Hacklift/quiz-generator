from typing import Any

from server.app.quiz.utils.grading import grade_answers


def grade_live_session(session: dict[str, Any], quiz: dict[str, Any]) -> dict[str, Any]:
    """Grade a stored live session from its immutable quiz content."""
    questions = quiz.get("questions") or []
    answer_by_index = {
        answer["question_index"]: answer.get("selected_answer", "")
        for answer in session.get("answers", [])
    }
    grading_payload = []
    for index, question in enumerate(questions):
        grading_payload.append(
            {
                "question": question.get("question", ""),
                "user_answer": answer_by_index.get(index, ""),
                "correct_answer": question.get("correct_answer") or question.get("answer"),
                "question_type": question.get("question_type")
                or quiz.get("quiz_type")
                or "multichoice",
                "source": question.get("source", "live"),
            }
        )

    graded_answers = grade_answers(grading_payload, "mock")
    indexed_answers = [
        {
            "question_index": index,
            "question": answer.get("question", ""),
            "selected_answer": str(answer.get("user_answer", "")),
            "correct_answer": str(answer.get("correct_answer", "")),
            "question_type": answer.get("question_type", ""),
            "is_correct": bool(answer.get("is_correct", False)),
        }
        for index, answer in enumerate(graded_answers)
    ]
    score = sum(1 for answer in graded_answers if answer.get("is_correct"))
    total = len(questions)
    return {
        "score": score,
        "percentage": round((score / total) * 100, 2) if total else 0,
        "graded_answers": indexed_answers,
    }
