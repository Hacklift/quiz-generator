import csv
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from server.app.quiz.utils.draw_wrapped_text import draw_wrapped_text
from server.app.quiz.utils.generate_pdf import _draw_watermark


def question_results(participant: dict[str, Any], question_count: int) -> list[str]:
    results_by_index = {
        result["question_index"]: result
        for result in participant.get("graded_answers", [])
        if isinstance(result.get("question_index"), int)
    }
    values = []
    for index in range(question_count):
        result = results_by_index.get(index)
        if not result or not result.get("selected_answer"):
            values.append("Unanswered")
        else:
            values.append("Correct" if result.get("is_correct") else "Incorrect")
    return values


def generate_live_results_csv(payload: dict[str, Any]) -> StringIO:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    question_count = payload["question_count"]
    writer.writerow(
        [
            "Participant",
            *[f"Q{number}" for number in range(1, question_count + 1)],
            "Score",
            "Percentage",
        ]
    )
    for participant in payload["participants"]:
        writer.writerow(
            [
                participant["participant_name"],
                *question_results(participant, question_count),
                f'{participant["score"]}/{participant["total_questions"]}',
                f'{participant["percentage"]}%',
            ]
        )
    buffer.seek(0)
    return buffer


def generate_live_results_txt(payload: dict[str, Any]) -> StringIO:
    buffer = StringIO()
    buffer.write(f'{payload["title"]}\n')
    buffer.write("Type: Live quiz session results\n\n")
    question_count = payload["question_count"]
    if not payload["participants"]:
        buffer.write("No completed participants.\n")
    for participant in payload["participants"]:
        buffer.write(f'Participant: {participant["participant_name"]}\n')
        for number, result in enumerate(
            question_results(participant, question_count), start=1
        ):
            buffer.write(f"Q{number}: {result}\n")
        buffer.write(f'Score: {participant["score"]}/{participant["total_questions"]}\n')
        buffer.write(f'Percentage: {participant["percentage"]}%\n\n')
    buffer.seek(0)
    return buffer


def generate_live_results_pdf(payload: dict[str, Any]) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter
    margin = 50
    line_width = page_width - (2 * margin)

    def start_page() -> float:
        _draw_watermark(pdf, page_width, page_height)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(margin, page_height - 50, payload["title"])
        pdf.setFont("Helvetica", 12)
        pdf.drawString(margin, page_height - 74, "Type: Live quiz session results")
        return page_height - 104

    y_position = start_page()
    question_count = payload["question_count"]
    if not payload["participants"]:
        pdf.drawString(margin, y_position, "No completed participants.")
    for participant in payload["participants"]:
        lines = [
            f'Participant: {participant["participant_name"]}',
            *[
                f"Q{number}: {result}"
                for number, result in enumerate(
                    question_results(participant, question_count), start=1
                )
            ],
            f'Score: {participant["score"]}/{participant["total_questions"]}',
            f'Percentage: {participant["percentage"]}%',
        ]
        for line in lines:
            if y_position < 65:
                pdf.showPage()
                y_position = start_page()
            y_position = draw_wrapped_text(
                pdf, line, margin, y_position, line_width
            )
        y_position -= 12
    pdf.save()
    buffer.seek(0)
    return buffer
