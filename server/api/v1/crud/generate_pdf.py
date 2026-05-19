from io import BytesIO

from reportlab.pdfgen import canvas

from typing import Any

from reportlab.lib.pagesizes import letter


from .draw_wrapped_text import draw_wrapped_text


def _draw_watermark(pdf: canvas.Canvas, page_width: float, page_height: float):
    pdf.saveState()
    pdf.setFillGray(0.9)
    pdf.setFont("Helvetica-Bold", 54)
    pdf.translate(page_width / 2, page_height / 2)
    pdf.rotate(35)
    pdf.drawCentredString(0, 0, "HQuiz")
    pdf.restoreState()


def _start_page(
    pdf: canvas.Canvas,
    payload: dict[str, Any],
    page_width: float,
    page_height: float,
    margin: float,
    line_width: float,
) -> float:
    _draw_watermark(pdf, page_width, page_height)
    y_position = page_height - 50
    title = payload.get("title") or "Quiz Download"
    quiz_type = payload.get("quiz_type") or "quiz"
    description = payload.get("description")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, y_position, title)
    y_position -= 24

    pdf.setFont("Helvetica", 12)
    y_position = draw_wrapped_text(pdf, f"Type: {quiz_type}", margin, y_position, line_width)
    if description:
        y_position = draw_wrapped_text(
            pdf,
            f"Description: {description}",
            margin,
            y_position,
            line_width,
        )
    y_position -= 10
    return y_position


def generate_pdf(payload: dict[str, Any]) -> BytesIO:
    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter
    margin = 50
    line_width = page_width - (2 * margin)
    y_position = _start_page(pdf, payload, page_width, page_height, margin, line_width)

    for item in payload.get("questions", []):
        question_number = item.get("number")
        question_prefix = f"Question {question_number}" if question_number else "Question"
        question = f"{question_prefix}: {item['question']}"
        y_position = draw_wrapped_text(pdf, question, margin, y_position, line_width)

        for option in item.get("options") or []:
            y_position = draw_wrapped_text(pdf, option, margin + 12, y_position, line_width - 12)

        answer = f"Answer: {item['answer']}"
        y_position = draw_wrapped_text(pdf, answer, margin, y_position, line_width)
        y_position -= 20

        if y_position < 50:
            pdf.showPage()
            y_position = _start_page(pdf, payload, page_width, page_height, margin, line_width)

    pdf.save()
    buffer.seek(0)
    return buffer
