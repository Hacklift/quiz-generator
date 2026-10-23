"""Presentation coverage, independent of database and network services."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from server.app.quiz.utils import live_results_pdf
from server.app.quiz.utils.live_results_export import generate_live_results_pdf


def sample_payload(participants=2, questions=3, long=False):
    return {
        "title": (
            "Évaluation <Sciences> & société " * 12 if long else "Évaluation & Sciences"
        ),
        "question_count": questions,
        "participants": [
            {
                "participant_name": f"Éloïse Müller {i}"
                + (" Longue dénomination" * 12 if long else ""),
                "score": 1,
                "total_questions": questions,
                "percentage": 33.33,
                "graded_answers": [
                    {"question_index": 0, "selected_answer": "A", "is_correct": True},
                    {"question_index": 1, "selected_answer": "B", "is_correct": False},
                ],
            }
            for i in range(participants)
        ],
    }


@pytest.mark.parametrize(
    "participants,questions,long",
    [(0, 0, False), (2, 3, False), (35, 30, False), (2, 80, True)],
)
def test_branded_pdf_content_and_pagination(participants, questions, long):
    payload = sample_payload(participants, questions, long)
    reader = PdfReader(generate_live_results_pdf(payload))
    texts = [page.extract_text() for page in reader.pages]
    text = "\n".join(texts)
    for number, page in enumerate(reader.pages, 1):
        assert float(page.mediabox.width) == pytest.approx(595.276, abs=0.01)
        assert "Live Quiz Results" in texts[number - 1]
        assert f"Page {number}" in texts[number - 1]
        assert page.images
        assert any(
            "Archivo" in str(font.get_object().get("/BaseFont"))
            for font in page["/Resources"]["/Font"].values()
        )
        assert b".039216 .196078 .392157 rg" in page.get_contents().get_data()
    assert "Évaluation" in text
    if not participants:
        assert "No completed participants." in text
    else:
        for i in range(participants):
            assert f"Éloïse Müller {i}" in text
        assert text.count("Score: 1/") >= participants
        assert text.count("Percentage: 33.33%") >= participants
        assert text.count("\nCorrect\n") == participants
        assert text.count("\nIncorrect\n") == participants
        assert text.count("\nUnanswered\n") == participants * (questions - 2)
    if questions > 30 or participants > 10:
        assert len(reader.pages) > 1
        assert all("Question" in item for item in texts[1:])


def test_backend_logo_matches_authoritative_frontend_asset():
    root = Path(__file__).resolve().parents[2]
    assert (live_results_pdf.ASSET_DIR / "logo.png").read_bytes() == (
        root / "client/public/images/logo.png"
    ).read_bytes()


def test_missing_branding_has_explicit_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(live_results_pdf, "ASSET_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="branding assets are missing or unreadable"):
        generate_live_results_pdf(sample_payload())


def test_both_archivo_weights_are_embedded_as_distinct_faces():
    reader = PdfReader(generate_live_results_pdf(sample_payload()))
    fonts = [
        font.get_object() for font in reader.pages[0]["/Resources"]["/Font"].values()
    ]
    archivo = [font for font in fonts if "Archivo" in str(font.get("/BaseFont"))]
    assert len(archivo) == 2
    assert len({str(font["/BaseFont"]) for font in archivo}) == 2
    assert all(
        font["/FontDescriptor"]["/FontFile2"].get_object().get_data()
        for font in archivo
    )


@pytest.mark.parametrize(
    "asset", ["logo.png", "Archivo-Regular.ttf", "Archivo-Bold.ttf"]
)
def test_corrupt_assets_fail_explicitly(monkeypatch, tmp_path, asset):
    from shutil import copytree

    target = tmp_path / "branding"
    copytree(live_results_pdf.ASSET_DIR, target)
    (target / asset).write_bytes(b"invalid asset")
    monkeypatch.setattr(live_results_pdf, "ASSET_DIR", target)
    with pytest.raises(RuntimeError, match="branding assets are missing or unreadable"):
        generate_live_results_pdf(sample_payload())


def test_minimal_participant_and_working_directory_independence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    payload = sample_payload(1, 0)
    payload["participants"][0].update(score=0, percentage=0, graded_answers=[])
    text = PdfReader(generate_live_results_pdf(payload)).pages[0].extract_text()
    assert "No questions." in text
    assert "Score: 0/0" in text
    assert "Percentage: 0%" in text
