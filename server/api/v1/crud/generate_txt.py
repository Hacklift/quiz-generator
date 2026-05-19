from io import StringIO
from typing import Any


def generate_txt(payload: dict[str, Any]):
    buffer = StringIO()

    title = payload.get("title") or "Quiz Download"
    quiz_type = payload.get("quiz_type") or "quiz"
    description = payload.get("description")

    buffer.write(f"{title}\n")
    buffer.write(f"Type: {quiz_type}\n")
    if description:
        buffer.write(f"Description: {description}\n")
    buffer.write("\n")

    for item in payload.get("questions", []):
        question_number = item.get("number")
        question_prefix = f"Question {question_number}" if question_number else "Question"
        buffer.write(f"{question_prefix}: {item['question']}\n")

        for option in item.get("options") or []:
            buffer.write(f"{option}\n")

        buffer.write(f"Answer: {item['answer']}\n\n")

    buffer.seek(0)
    return buffer
