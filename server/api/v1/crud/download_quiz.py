from .download.download_quiz import download_mock_quiz, download_quiz_by_id
from .generate_csv import generate_csv
from .generate_docx import generate_docx
from .generate_pdf import generate_pdf
from .generate_txt import generate_txt
from ..db import (
    quiz_data_multiple_choice,
    quiz_data_open_ended,
    quiz_data_true_false,
)


def download_quiz(format: str, question_type: str, num_question: int):
    return download_mock_quiz(format, question_type, num_question)


__all__ = [
    "download_quiz",
    "download_quiz_by_id",
    "generate_csv",
    "generate_docx",
    "generate_pdf",
    "generate_txt",
    "quiz_data_multiple_choice",
    "quiz_data_open_ended",
    "quiz_data_true_false",
]
