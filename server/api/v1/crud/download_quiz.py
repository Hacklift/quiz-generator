from fastapi import HTTPException

from fastapi.responses import StreamingResponse

from .generate_csv import generate_csv

from .generate_docx import generate_docx

from .generate_pdf import generate_pdf

from .generate_txt import generate_txt

from ..db import (

    quiz_data_multiple_choice,

    quiz_data_open_ended,

    quiz_data_true_false

)


def download_quiz(format: str, question_type: str, num_question: int) -> StreamingResponse:

    if question_type == "multichoice":

        quiz_data = quiz_data_multiple_choice

    elif question_type == "true-false":

        quiz_data = quiz_data_true_false

    elif question_type == "open-ended":

        quiz_data = quiz_data_open_ended

    else:

        raise HTTPException(status_code=400, detail="Unsupported question_type")


    sliced_quiz_data = quiz_data[:num_question]


    if format == "txt":

        buffer = generate_txt(sliced_quiz_data)

        content_type = "text/plain"

    elif format == "csv":

        buffer = generate_csv(sliced_quiz_data)

        content_type = "text/csv"

    elif format == "pdf":

        buffer = generate_pdf(sliced_quiz_data)

        content_type = "application/pdf"

    elif format == "docx":

        buffer = generate_docx(sliced_quiz_data)

        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    else:

        raise HTTPException(status_code=400, detail="Unsupported file format")


    return StreamingResponse(

        buffer, media_type=content_type, headers={

            "Content-Disposition": f"attachment; filename=quiz_data.{format}"

        }

    )

