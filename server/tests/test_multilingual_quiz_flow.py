import json
from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfReader

from server.app.quiz.utils.structured_generation import parse_generated_quiz
from server.app.quiz.utils.session_grading import grade_live_session
from server.app.quiz.utils.generate_txt import generate_txt
from server.app.quiz.utils.generate_pdf import generate_pdf
from server.app.quiz.utils.generate_docx import generate_docx
from server.app.quiz.services.download_service import _build_download_payload, _content_disposition


@pytest.mark.parametrize("locale,question,explanation,answer", [
    ("es", "¿La Tierra es plana?", "La Tierra es aproximadamente esférica.", "Falso"),
    ("fr", "La Terre est-elle plate ?", "La Terre est approximativement sphérique.", "Faux"),
    ("de", "Ist die Erde flach?", "Die Erde ist annähernd kugelförmig.", "Falsch"),
])
def test_generated_locale_survives_grading_and_export(locale, question, explanation, answer):
    wire = {"content_locale": locale, "title": question, "description": explanation,
            "questions": [{"question": question, "explanation": explanation, "correct_boolean": False,
                           "options": ["Wahr", "Falsch"] if locale == "de" else None}]}
    quiz = parse_generated_quiz(json.dumps(wire), locale=locale, question_type="true-false", count=1)
    quiz["quiz_type"] = "true-false"
    assert quiz["questions"][0]["answer"] == answer
    for selected in ("0", answer):
        result = grade_live_session({"answers": [{"question_index": 0, "selected_answer": selected}]}, quiz)
        assert result["score"] == 1
        assert result["content_locale"] == locale
        assert result["graded_answers"][0]["correct_answer"] == answer
        assert result["graded_answers"][0]["explanation"] == explanation
    payload = _build_download_payload(title=question, description=explanation, quiz_type="true-false",
                                     questions=quiz["questions"], content_locale=locale)
    txt = generate_txt(payload).getvalue()
    assert question in txt and explanation in txt and answer in txt
    doc = Document(generate_docx(payload))
    doc_text = "\n".join(p.text for p in doc.paragraphs)
    pdf_text = "\n".join(p.extract_text() for p in PdfReader(generate_pdf(payload)).pages)
    if locale in {"es", "fr"}:
        label = "Respuesta:" if locale == "es" else "Réponse:"
        assert label in txt and label in doc_text and label in pdf_text
        assert "Answer:" not in txt


def test_unicode_download_filename_has_rfc5987_encoding():
    header = _content_disposition("日本語.txt")
    assert "filename*=UTF-8''" in header
    header.encode("latin-1")
