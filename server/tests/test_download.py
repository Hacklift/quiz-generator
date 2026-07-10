import pytest

from unittest.mock import patch
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from bson import ObjectId
from pydantic import ValidationError

from fastapi import HTTPException
from fastapi import Response

from fastapi.responses import StreamingResponse

from io import BytesIO

from server.app.quiz.routes.downloads import download_quiz_handler
from server.app.quiz.routes.downloads import download_quiz_from_payload_handler
from server.main import limiter
from server.app.quiz.schemas.download_schemas import DownloadQuizRequestModel
from server.app.quiz.schemas.download_query import DownloadQuizQuery

from docx import Document

from pypdf import PdfReader

from server.app.quiz.services.download_service import (
    build_download_filename,
    download_mock_quiz,
    download_quiz_by_id,
)
from server.app.quiz.utils.generate_docx import generate_docx
from server.app.quiz.utils.generate_json import generate_json
from server.app.quiz.utils.generate_pdf import generate_pdf
from server.app.quiz.utils.generate_txt import generate_txt


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    original_enabled = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original_enabled


def mock_generate_file(data):

    """Mock function to return a file-like object."""

    return BytesIO(b"mock file content")


@pytest.mark.parametrize("format, content_type", [

    ("txt", "text/plain"),

    ("json", "application/json"),

    ("pdf", "application/pdf"),

    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),

])

@patch("server.app.quiz.services.download_service.mock_multiple_choice_questions", return_value=[{"q": "A"}] * 10)

@patch("server.app.quiz.services.download_service.generate_txt", side_effect=mock_generate_file)

@patch("server.app.quiz.services.download_service.generate_json", side_effect=mock_generate_file)

@patch("server.app.quiz.services.download_service.generate_pdf", side_effect=mock_generate_file)

@patch("server.app.quiz.services.download_service.generate_docx", side_effect=mock_generate_file)

def test_download_quiz_valid_formats(

    mock_docx, mock_pdf, mock_json, mock_txt, mock_questions, format, content_type

):

    """Test if download_quiz correctly returns a StreamingResponse with valid formats."""

    response = download_mock_quiz(format=format, question_type="multichoice", num_question=5)


    assert isinstance(response, StreamingResponse)

    assert response.media_type == content_type

    assert response.headers["Content-Disposition"] == f'attachment; filename="Multichoice Quiz.{format}"'


def test_build_download_filename_preserves_readable_quiz_title():
    assert (
        build_download_filename("Circuit Breaker in systems design", "pdf")
        == "Circuit Breaker in systems design.pdf"
    )
    assert build_download_filename('Circuit/Breaker: "Retry"', "txt") == "Circuit Breaker Retry.txt"


@pytest.mark.parametrize("question_type", ["invalid-type", "random"])

def test_download_quiz_invalid_question_type(question_type):

    """Test if download_quiz raises HTTPException for unsupported question types."""

    with pytest.raises(HTTPException) as exc:

        download_mock_quiz(format="txt", question_type=question_type, num_question=5)

    assert exc.value.status_code == 400

    assert "Unsupported question_type" in exc.value.detail


@pytest.mark.parametrize("format", ["xml", "csv", "xlsx"])

def test_download_quiz_invalid_format(format):

    """Test if download_quiz raises HTTPException for unsupported file formats."""

    with pytest.raises(HTTPException) as exc:

        download_mock_quiz(format=format, question_type="multichoice", num_question=5)

    assert exc.value.status_code == 400

    assert "Unsupported file format" in exc.value.detail




@pytest.mark.parametrize("format,question_type,num_question", [

    ("txt", "multichoice", 5),

    ("json", "true-false", 3),

    ("pdf", "open-ended", 2),

    ("docx", "multichoice", 4),

])

@pytest.mark.asyncio
async def test_download_quiz_api_valid(format, question_type, num_question):

    response = await download_quiz_handler(
        request=MagicMock(),
        response=Response(),
        query=DownloadQuizQuery(
            format=format,
            question_type=question_type,
            num_question=num_question,
        ),
    )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == {
        "txt": "text/plain",
        "json": "application/json",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }[format]
    assert "Content-Disposition" in response.headers
    expected_title = {
        "multichoice": "Multichoice Quiz",
        "true-false": "True False Quiz",
        "open-ended": "Open Ended Quiz",
    }[question_type]
    assert response.headers["Content-Disposition"] == f'attachment; filename="{expected_title}.{format}"'




@pytest.mark.parametrize("format,question_type,num_question,expected_status", [

    ("txt", "invalid-type", 5, 400),

    ("json", "true-false", 0, 422),

])
@pytest.mark.asyncio
async def test_download_quiz_api_invalid(format, question_type, num_question, expected_status):
    if expected_status == 422:
        with pytest.raises(ValidationError):
            DownloadQuizQuery(
                format=format,
                question_type=question_type,
                num_question=num_question,
            )
        return

    with pytest.raises(HTTPException) as exc:
        await download_quiz_handler(
            request=MagicMock(),
            response=Response(),
            query=DownloadQuizQuery(
                format=format,
                question_type=question_type,
                num_question=num_question,
            ),
        )

    assert exc.value.status_code == expected_status
    assert exc.value.detail
    assert exc.value.detail




@pytest.fixture
def sample_download_payload():
    return {
        "title": "Science Drill",
        "description": "A printable study quiz",
        "quiz_type": "multichoice",
        "questions": [
            {
                "number": 1,
                "question": "What is the capital of France?",
                "options": [
                    "A) Paris",
                    "B) London",
                    "C) Berlin",
                    "D) Rome",
                ],
                "answer": "A) Paris",
            },
            {
                "number": 2,
                "question": "Venus is the hottest planet in the solar system.",
                "options": ["A) true", "B) false"],
                "answer": "A) true",
            },
            {
                "number": 3,
                "question": "Explain the process of photosynthesis.",
                "options": [],
                "answer": "Photosynthesis is the process by which green plants and some organisms use sunlight to synthesize foods with the help of chlorophyll.",
            },
        ],
    }


def test_generate_json(sample_download_payload):
    buffer = generate_json(sample_download_payload)
    content = buffer.getvalue().strip()

    assert '"title": "Science Drill"' in content
    assert '"number": 1' in content
    assert '"question": "What is the capital of France?"' in content


def test_generate_txt(sample_download_payload):
    buffer = generate_txt(sample_download_payload)

    content = buffer.getvalue().strip()


    assert "Science Drill" in content
    assert "Type: multichoice" in content
    assert "Question 1: What is the capital of France?" in content

    assert "A) Paris" in content

    assert "Answer: A) Paris" in content


    assert "Question 2: Venus is the hottest planet in the solar system." in content

    assert "A) true" in content

    assert "Answer: A) true" in content


    assert "Question 3: Explain the process of photosynthesis." in content

    assert "Answer: Photosynthesis is the process" in content



def test_generate_docx(sample_download_payload):

    buffer = generate_docx(sample_download_payload)


    buffer.seek(0)

    doc = Document(buffer)


    paragraphs = [para.text for para in doc.paragraphs]


    assert "Science Drill" in paragraphs
    assert "Type: multichoice" in paragraphs
    assert "Question 1: What is the capital of France?" in paragraphs

    assert "A) Paris" in paragraphs

    assert "Answer: A) Paris" in paragraphs


    assert "Question 2: Venus is the hottest planet in the solar system." in paragraphs

    assert "A) true" in paragraphs

    assert "Answer: A) true" in paragraphs


    assert "Question 3: Explain the process of photosynthesis." in paragraphs

    assert "Answer: Photosynthesis is the process" in " ".join(paragraphs)



def test_generate_pdf(sample_download_payload):

    buffer = generate_pdf(sample_download_payload)

    buffer.seek(0)


    reader = PdfReader(buffer)

    content = ""

    for page in reader.pages:

        content += page.extract_text()


    assert "Science Drill" in content
    assert "Type: multichoice" in content
    assert "Question 1: What is the capital of France?" in content

    assert "A) Paris" in content

    assert "Answer: A) Paris" in content


    assert "Question 2: Venus is the hottest planet in the solar system." in content

    assert "A) true" in content

    assert "Answer: A) true" in content


    assert "Question 3: Explain the process of photosynthesis." in content

    assert "Answer: Photosynthesis is the process" in content


@pytest.mark.asyncio
async def test_download_quiz_from_payload_supports_current_displayed_quiz():
    response = await download_quiz_from_payload_handler(
        request=MagicMock(),
        response=Response(),
        payload=DownloadQuizRequestModel(
            format="json",
            title="Current Quiz",
            description="Generated on the client",
            quiz_type="multichoice",
            questions=[
                {
                    "question": "Which option is correct?",
                    "options": ["Correct", "Wrong"],
                    "answer": "Correct",
                }
            ],
        ),
    )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "application/json"
    assert response.headers["Content-Disposition"] == 'attachment; filename="Current Quiz.json"'


@pytest.mark.asyncio
async def test_download_quiz_by_id_reads_canonical_v2_quiz_and_normalizes_answers():
    v2_collection = AsyncMock()

    v2_collection.find_one.return_value = {
        "_id": ObjectId("69e78f93594339fd166131ea"),
        "title": "AI Automation Basics",
        "quiz_type": "multichoice",
        "questions": [
            {
                "question": "What is the main goal of AI automation?",
                "options": [
                    "A) To replace all human jobs",
                    "B) To perform tasks without human intervention",
                ],
                "correct_answer": "B) To perform tasks without human intervention",
            }
        ],
    }
    with patch(
        "server.app.quiz.services.download_service.get_quizzes_v2_collection",
        return_value=v2_collection,
    ), patch(
        "server.app.quiz.services.download_service.generate_txt",
        side_effect=generate_txt,
    ):
        response = await download_quiz_by_id(
            quiz_id="69e78f93594339fd166131ea",
            file_format="txt",
        )

    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/plain"
    assert response.headers["Content-Disposition"] == 'attachment; filename="AI Automation Basics.txt"'
