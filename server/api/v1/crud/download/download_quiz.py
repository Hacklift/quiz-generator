from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId
from bson.errors import InvalidId
from .....app.db.core.connection import get_ai_generated_quizzes_collection
from ..generate_csv import generate_csv
from ..generate_docx import generate_docx
from ..generate_pdf import generate_pdf
from ..generate_txt import generate_txt
from ...db import (
    quiz_data_multiple_choice,
    quiz_data_open_ended,
    quiz_data_true_false
)
import logging

logger = logging.getLogger(__name__)


def download_mock_quiz(format: str, question_type: str, num_question: int) -> StreamingResponse:
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



async def download_quiz_by_id(
    quiz_id: str,
    file_format: str,
    user_id: str
) -> StreamingResponse:
    """
    Download an existing quiz by its MongoDB ObjectId.
    Extracts only the 'questions' list to match existing generators.
    """

    collection = get_ai_generated_quizzes_collection()
    logger.info(f"pulling quiz {quiz_id} from database")

    try:
        object_id = ObjectId(quiz_id)
    except InvalidId:
        logger.warning(f"Invalid quiz_id format: {quiz_id}")
        raise HTTPException(status_code=400, detail="Invalid quiz_id (must be a valid ObjectId)")

    quiz_doc = await collection.find_one({"_id": object_id})
    if not quiz_doc:
        logger.warning(f"unable to pull quiz {quiz_id} from db")
        raise HTTPException(status_code=404, detail=f"Quiz not found for id {quiz_id}")

    # STEP 3 — Extract compatible quiz structure
    quiz_data = quiz_doc.get("questions", [])
    if not quiz_data:
        logger.warning(f"Quiz with id {quiz_id} contains no questions")
        raise HTTPException(
            status_code=400,
            detail=f"Quiz with id {quiz_id} contains no questions"
        )

    # STEP 4 — Generate the downloadable file
    if file_format == "txt":
        buffer = generate_txt(quiz_data)
        content_type = "text/plain"

    elif file_format == "csv":
        buffer = generate_csv(quiz_data)
        content_type = "text/csv"

    elif file_format == "pdf":
        buffer = generate_pdf(quiz_data)
        content_type = "application/pdf"

    elif file_format == "docx":
        buffer = generate_docx(quiz_data)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    logger.info(f"download of quiz {quiz_id} should commence immediately!")

    return StreamingResponse(
        buffer,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=quiz_{quiz_id}.{file_format}"
        }
    )

