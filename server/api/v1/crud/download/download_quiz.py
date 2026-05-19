from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId
from bson.errors import InvalidId
from .....app.db.core.connection import get_ai_generated_quizzes_collection
from .....app.db.core.connection import get_quizzes_collection
from .....app.db.core.connection import get_quizzes_v2_collection
from ..generate_docx import generate_docx
from ..generate_json import generate_json
from ..generate_pdf import generate_pdf
from ..generate_txt import generate_txt
from ...db import (
    quiz_data_multiple_choice,
    quiz_data_open_ended,
    quiz_data_true_false
)
import logging

logger = logging.getLogger(__name__)


def _build_default_title(question_type: str | None) -> str:
    if not question_type:
        return "Quiz Download"
    return f"{question_type.replace('-', ' ').title()} Quiz"


def _normalize_option(option: str, index: int) -> str:
    stripped = option.strip()
    if len(stripped) > 2 and stripped[1] == ")" and stripped[0].isalpha():
        return stripped
    if len(stripped) > 2 and stripped[1] == "." and stripped[0].isalpha():
        return stripped
    option_label = chr(ord("A") + index)
    return f"{option_label}) {stripped}"


def _normalize_questions_for_download(questions: list[dict]) -> list[dict]:
    normalized_questions = []
    for index, question in enumerate(questions, start=1):
        raw_options = question.get("options") or []
        normalized_options = [
            _normalize_option(option, option_index)
            for option_index, option in enumerate(raw_options)
        ]
        normalized_questions.append(
            {
                "number": index,
                "question": question.get("question"),
                "options": normalized_options,
                "answer": question.get("answer") or question.get("correct_answer"),
            }
        )
    return normalized_questions


def _build_download_payload(
    *,
    title: str | None,
    description: str | None,
    quiz_type: str | None,
    questions: list[dict],
) -> dict:
    return {
        "title": title or _build_default_title(quiz_type),
        "description": description,
        "quiz_type": quiz_type,
        "questions": _normalize_questions_for_download(questions),
    }


def _render_download_stream(payload: dict, file_format: str) -> StreamingResponse:
    if file_format == "txt":
        buffer = generate_txt(payload)
        content_type = "text/plain"
    elif file_format == "json":
        buffer = generate_json(payload)
        content_type = "application/json"
    elif file_format == "pdf":
        buffer = generate_pdf(payload)
        content_type = "application/pdf"
    elif file_format == "docx":
        buffer = generate_docx(payload)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    return StreamingResponse(buffer, media_type=content_type)


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
    payload = _build_download_payload(
        title=None,
        description="Generated from the quiz mock dataset.",
        quiz_type=question_type,
        questions=sliced_quiz_data,
    )
    response = _render_download_stream(payload, format)

    response.headers.update(
        {
            "Content-Disposition": f"attachment; filename=quiz_data.{format}"
        }
    )
    return response


def download_quiz_from_payload(
    *,
    title: str | None,
    description: str | None,
    quiz_type: str | None,
    questions: list[dict],
    file_format: str,
) -> StreamingResponse:
    if not questions:
        raise HTTPException(status_code=400, detail="Quiz payload contains no questions")

    payload = _build_download_payload(
        title=title,
        description=description,
        quiz_type=quiz_type,
        questions=questions,
    )
    response = _render_download_stream(payload, file_format)
    filename_base = (payload["title"] or "quiz").strip().replace(" ", "_").lower()
    response.headers.update(
        {
            "Content-Disposition": f"attachment; filename={filename_base}.{file_format}"
        }
    )
    return response



async def download_quiz_by_id(
    quiz_id: str,
    file_format: str,
    user_id: str | None = None,
) -> StreamingResponse:
    """
    Download an existing quiz by its MongoDB ObjectId.
    Extracts only the 'questions' list to match existing generators.
    """
    v2_collection = get_quizzes_v2_collection()
    legacy_ai_collection = get_ai_generated_quizzes_collection()
    legacy_manual_collection = get_quizzes_collection()
    logger.info(f"pulling quiz {quiz_id} from database")

    try:
        object_id = ObjectId(quiz_id)
    except InvalidId:
        logger.warning(f"Invalid quiz_id format: {quiz_id}")
        raise HTTPException(status_code=400, detail="Invalid quiz_id (must be a valid ObjectId)")

    payload = None
    quiz_doc = await v2_collection.find_one({"_id": object_id})
    if quiz_doc:
        payload = _build_download_payload(
            title=quiz_doc.get("title"),
            description=quiz_doc.get("description"),
            quiz_type=quiz_doc.get("quiz_type"),
            questions=quiz_doc.get("questions", []),
        )
    else:
        quiz_doc = await legacy_ai_collection.find_one({"_id": object_id})
        if quiz_doc:
            payload = _build_download_payload(
                title=quiz_doc.get("profession") or quiz_doc.get("title"),
                description=quiz_doc.get("custom_instruction") or quiz_doc.get("description"),
                quiz_type=quiz_doc.get("question_type") or quiz_doc.get("quiz_type"),
                questions=quiz_doc.get("questions", []),
            )
        else:
            quiz_doc = await legacy_manual_collection.find_one({"_id": object_id})
            if quiz_doc:
                payload = _build_download_payload(
                    title=quiz_doc.get("title"),
                    description=quiz_doc.get("description"),
                    quiz_type=quiz_doc.get("question_type") or quiz_doc.get("quiz_type"),
                    questions=quiz_doc.get("questions", []),
                )

    if not quiz_doc:
        logger.warning(f"unable to pull quiz {quiz_id} from db")
        raise HTTPException(status_code=404, detail=f"Quiz not found for id {quiz_id}")

    owner_user_id = (
        quiz_doc.get("owner_user_id")
        or quiz_doc.get("user_id")
        or quiz_doc.get("owner_id")
    )
    if user_id is not None and owner_user_id and str(owner_user_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # STEP 3 — Extract compatible quiz structure
    if not payload or not payload["questions"]:
        logger.warning(f"Quiz with id {quiz_id} contains no questions")
        raise HTTPException(
            status_code=400,
            detail=f"Quiz with id {quiz_id} contains no questions"
        )

    # STEP 4 — Generate the downloadable file
    response = _render_download_stream(payload, file_format)
    logger.info(f"download of quiz {quiz_id} should commence immediately!")
    response.headers.update(
        {
            "Content-Disposition": f"attachment; filename=quiz_{quiz_id}.{file_format}"
        }
    )
    return response
