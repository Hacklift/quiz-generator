import pytest

from unittest.mock import patch

from fastapi import HTTPException

from fastapi.responses import StreamingResponse

from fastapi.testclient import TestClient

from io import BytesIO

from server.main import app

from docx import Document

from pypdf import PdfReader

from server.api.v1.crud.download_quiz import (

    download_quiz,

    generate_csv,

    generate_docx,

    generate_pdf,

    generate_txt

    )


client = TestClient(app)


def mock_generate_file(data):

    """Mock function to return a file-like object."""

    return BytesIO(b"mock file content")


@pytest.mark.parametrize("format, content_type", [

    ("txt", "text/plain"),

    ("csv", "text/csv"),

    ("pdf", "application/pdf"),

    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),

])

@patch("server.api.v1.crud.download_quiz.quiz_data_multiple_choice", new=[{"q": "A"}] * 10)

@patch("server.api.v1.crud.download_quiz.generate_txt", side_effect=mock_generate_file)

@patch("server.api.v1.crud.download_quiz.generate_csv", side_effect=mock_generate_file)

@patch("server.api.v1.crud.download_quiz.generate_pdf", side_effect=mock_generate_file)

@patch("server.api.v1.crud.download_quiz.generate_docx", side_effect=mock_generate_file)

def test_download_quiz_valid_formats(

    mock_txt, mock_csv, mock_pdf, mock_docx, format, content_type

):

    """Test if download_quiz correctly returns a StreamingResponse with valid formats."""

    response = download_quiz(format=format, question_type="multichoice", num_question=5)


    assert isinstance(response, StreamingResponse)

    assert response.media_type == content_type

    assert response.headers["Content-Disposition"] == f"attachment; filename=quiz_data.{format}"


@pytest.mark.parametrize("question_type", ["invalid-type", "random"])

def test_download_quiz_invalid_question_type(question_type):

    """Test if download_quiz raises HTTPException for unsupported question types."""

    with pytest.raises(HTTPException) as exc:

        download_quiz(format="txt", question_type=question_type, num_question=5)

    assert exc.value.status_code == 400

    assert "Unsupported question_type" in exc.value.detail


@pytest.mark.parametrize("format", ["xml", "json", "xlsx"])

def test_download_quiz_invalid_format(format):

    """Test if download_quiz raises HTTPException for unsupported file formats."""

    with pytest.raises(HTTPException) as exc:

        download_quiz(format=format, question_type="multichoice", num_question=5)

    assert exc.value.status_code == 400

    assert "Unsupported file format" in exc.value.detail




@pytest.mark.parametrize("format,question_type,num_question", [

    ("txt", "multichoice", 5),

    ("csv", "true-false", 3),

    ("pdf", "open-ended", 2),

    ("docx", "multichoice", 4),

])

def test_download_quiz_api_valid(format, question_type, num_question):

    response = client.get(

        "/download-quiz",

        params={

            "format": format,

            "question_type": question_type,

            "num_question": num_question,

            "user_id": "test_user"

        }

    )


    assert response.status_code == 200

    assert "Content-Disposition" in response.headers

    assert f"attachment; filename=quiz_data.{format}" in response.headers["Content-Disposition"]

    assert response.content




@pytest.mark.parametrize("format,question_type,num_question,expected_status", [

    ("txt", "invalid-type", 5, 400),

    ("csv", "true-false", 0, 422),

])

def test_download_quiz_api_invalid(format, question_type, num_question, expected_status):

    response = client.get(

        "/download-quiz",

        params={

            "format": format,

            "question_type": question_type,

            "num_question": num_question,

            "user_id": "test_user"

        }

    )


    assert response.status_code == expected_status

    assert "application/json" in response.headers["content-type"]

    assert "detail" in response.json()




@pytest.fixture

def sample_quiz_data():

    return [

        {

            "question": "What is the capital of France?",

            "options": ["Paris", "London", "Berlin", "Rome"],

            "answer": "Paris"

        },

        {

            "question": "Venus is the hottest planet in the solar system.",

            "options": ["true", "false"],

            "answer": "true"

        },

        {

            "question": "Explain the process of photosynthesis.",

            "answer": "Photosynthesis is the process by which green plants and some organisms use sunlight to synthesize foods with the help of chlorophyll. It involves the conversion of carbon dioxide and water into glucose and oxygen."

        }

    ]


def test_generate_csv(sample_quiz_data):

    buffer = generate_csv(sample_quiz_data)

    content = buffer.getvalue().strip()


    assert "Question,Options,Answer" in content

    assert "What is the capital of France?" in content

    assert "\"Paris, London, Berlin, Rome\"" in content

    assert "Paris" in content


    assert "Venus is the hottest planet in the solar system." in content

    assert "\"true, false\"" in content

    assert "true" in content


    assert "Explain the process of photosynthesis." in content

    assert ",,Photosynthesis is the process" in content



def test_generate_txt(sample_quiz_data):

    buffer = generate_txt(sample_quiz_data)

    content = buffer.getvalue().strip()


    assert "Question: What is the capital of France?" in content

    assert "Options: Paris, London, Berlin, Rome" in content

    assert "Answer: Paris" in content


    assert "Question: Venus is the hottest planet in the solar system." in content

    assert "Options: true, false" in content

    assert "Answer: true" in content


    assert "Question: Explain the process of photosynthesis." in content

    assert "Answer: Photosynthesis is the process" in content



def test_generate_docx(sample_quiz_data):

    buffer = generate_docx(sample_quiz_data)


    buffer.seek(0)

    doc = Document(buffer)


    paragraphs = [para.text for para in doc.paragraphs]


    assert "Question: What is the capital of France?" in paragraphs

    assert "Options: Paris, London, Berlin, Rome" in paragraphs

    assert "Answer: Paris" in paragraphs


    assert "Question: Venus is the hottest planet in the solar system." in paragraphs

    assert "Options: true, false" in paragraphs

    assert "Answer: true" in paragraphs


    assert "Question: Explain the process of photosynthesis." in paragraphs

    assert "Answer: Photosynthesis is the process" in " ".join(paragraphs)



def test_generate_pdf(sample_quiz_data):

    buffer = generate_pdf(sample_quiz_data)

    buffer.seek(0)


    reader = PdfReader(buffer)

    content = ""

    for page in reader.pages:

        content += page.extract_text()


    assert "Question: What is the capital of France?" in content

    assert "Options: Paris, London, Berlin, Rome" in content

    assert "Answer: Paris" in content


    assert "Question: Venus is the hottest planet in the solar system." in content

    assert "Options: true, false" in content

    assert "Answer: true" in content


    assert "Question: Explain the process of photosynthesis." in content

    assert "Answer: Photosynthesis is the process" in content



