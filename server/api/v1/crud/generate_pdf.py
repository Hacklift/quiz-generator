from io import BytesIO

from reportlab.pdfgen import canvas

from typing import List

from reportlab.lib.pagesizes import letter


from .draw_wrapped_text import draw_wrapped_text



def generate_pdf(data: List[dict]) -> BytesIO:

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=letter)

    page_width, page_height = letter

    margin = 50

    line_width = page_width - (2 * margin)

    y_position = page_height - 50


    for item in data:

        question = f"Question: {item['question']}"

        y_position = draw_wrapped_text(pdf, question, margin, y_position, line_width)


        if 'options' in item:

            options = "Options: " + ", ".join(item['options'])

            y_position = draw_wrapped_text(pdf, options, margin, y_position, line_width)


        answer = f"Answer: {item['answer']}"

        y_position = draw_wrapped_text(pdf, answer, margin, y_position, line_width)


        y_position -= 20


        if y_position < 50:

            pdf.showPage()

            y_position = page_height - 50


    pdf.save()

    buffer.seek(0)

    return buffer

