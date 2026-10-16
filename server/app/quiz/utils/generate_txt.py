from .export_labels import export_labels, export_type
from io import StringIO
from typing import Any


def generate_txt(payload: dict[str, Any]):
    buffer = StringIO()

    labels = export_labels(payload)
    title = payload.get("title") or labels["title"]
    quiz_type = export_type(payload)
    description = payload.get("description")

    buffer.write(f"{title}\n")
    buffer.write(f"{labels['type']}: {quiz_type}\n")
    if description:
        buffer.write(f"{labels['description']}: {description}\n")
    buffer.write("\n")

    for item in payload.get("questions", []):
        question_number = item.get("number")
        question_prefix = f"{labels['question']} {question_number}" if question_number else labels["question"]
        buffer.write(f"{question_prefix}: {item['question']}\n")

        for option in item.get("options") or []:
            buffer.write(f"{option}\n")

        buffer.write(f"{labels['answer']}: {item['answer']}\n")
        if item.get("explanation"):
            buffer.write(f"{labels['explanation']}: {item['explanation']}\n")
        buffer.write("\n")

    buffer.seek(0)
    return buffer
