"""Presentation-only Live Quiz report; assets ship inside the backend image."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "branding"
BRAND = colors.HexColor("#0a3264")
INK = colors.HexColor("#201e1d")
PAPER = colors.HexColor("#f3f2f2")
TINT = colors.HexColor("#e7ecf3")


def build_pdf(payload, question_results):
    """Render persisted grades without recomputing scores or correctness.

    Missing/corrupt assets fail explicitly, rather than silently delivering an
    unbranded report. No frontend filesystem or network is needed at runtime.
    """
    try:
        logo = ImageReader(str(ASSET_DIR / "logo.png"))
        logo_width, logo_height = logo.getSize()
        for weight in ("Regular", "Bold"):
            pdfmetrics.registerFont(
                TTFont(f"Archivo-{weight}", str(ASSET_DIR / f"Archivo-{weight}.ttf"))
            )
    except Exception as exc:
        raise RuntimeError(
            "Live results PDF branding assets are missing or unreadable"
        ) from exc

    regular = ParagraphStyle(
        "Body",
        fontName="Archivo-Regular",
        fontSize=10,
        leading=15,
        textColor=INK,
        alignment=TA_LEFT,
        splitLongWords=True,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=regular,
        fontName="Archivo-Bold",
        fontSize=13,
        leading=18,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    )
    score_style = ParagraphStyle("Score", parent=regular, keepWithNext=True)
    title = ParagraphStyle(
        "Title", parent=heading, fontSize=21, leading=27, spaceBefore=0, spaceAfter=12
    )

    def p(value, style=regular):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)

    buffer = BytesIO()
    width, height = A4
    margin = 42
    available = width - 2 * margin
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=116,
        bottomMargin=52,
        title=str(payload["title"]),
        author="Quizwerk",
    )

    def page_chrome(pdf, document):
        pdf.saveState()
        pdf.setFillColor(BRAND)
        pdf.rect(0, height - 88, width, 88, fill=1, stroke=0)
        display_width = min(108, 80 * logo_width / logo_height)
        display_height = display_width * logo_height / logo_width
        pdf.drawImage(
            logo,
            margin,
            height - 44 - display_height / 2,
            width=display_width,
            height=display_height,
            mask="auto",
        )
        pdf.setFillColor(colors.white)
        pdf.setFont("Archivo-Bold", 17)
        pdf.drawString(margin + 112, height - 42, "Live Quiz Results")
        pdf.setFont("Archivo-Regular", 9)
        pdf.drawString(margin + 112, height - 60, "Live quiz session results")
        pdf.setStrokeColor(TINT)
        pdf.line(margin, 37, width - margin, 37)
        pdf.setFillColor(INK)
        pdf.setFont("Archivo-Regular", 8)
        pdf.drawString(margin, 23, "Quizwerk  /  Live Quiz Results")
        pdf.drawRightString(width - margin, 23, f"Page {document.page}")
        pdf.restoreState()

    participants = payload["participants"]
    count = payload["question_count"]
    story = [p(payload["title"], title)]
    average = (
        f"{sum(row['percentage'] for row in participants) / len(participants):.2f}%"
        if participants
        else "—"
    )
    summary = Table(
        [
            [p("PARTICIPANTS"), p("QUESTIONS"), p("AVERAGE PERCENTAGE")],
            [p(len(participants), heading), p(count, heading), p(average, heading)],
        ],
        colWidths=[available * 0.29, available * 0.25, available * 0.46],
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TINT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.extend([summary, Spacer(1, 8)])
    if not participants:
        story.extend([Spacer(1, 14), p("No completed participants.")])
    for participant in participants:
        story.append(Spacer(1, 16))
        rows = [
            [p(f"Participant: {participant['participant_name']}", heading), ""],
            [
                p(
                    f"Score: {participant['score']}/{participant['total_questions']}"
                    f"    •    Percentage: {participant['percentage']}%",
                    score_style,
                ),
                "",
            ],
            [p("Question"), p("Result")],
        ]
        for number, result in enumerate(question_results(participant, count), 1):
            status_style = ParagraphStyle(
                "Status",
                parent=regular,
                textColor=BRAND if result == "Correct" else INK,
                fontName="Archivo-Bold" if result == "Correct" else "Archivo-Regular",
            )
            rows.append([p(f"Q{number}"), p(result, status_style)])
        if len(rows) == 3:
            rows.append([p("—"), p("No questions.")])
        table = Table(
            rows,
            colWidths=[available * 0.23, available * 0.77],
            repeatRows=3,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (-1, 0)),
                    ("SPAN", (0, 1), (-1, 1)),
                    ("BACKGROUND", (0, 2), (-1, 2), TINT),
                    ("ROWBACKGROUNDS", (0, 3), (-1, -1), [colors.white, PAPER]),
                    ("LINEBELOW", (0, 2), (-1, 2), 1, BRAND),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)
    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    buffer.seek(0)
    return buffer
