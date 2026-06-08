from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from server.app.core.config import settings
from server.app.core.dependencies import get_current_user_optional
from server.app.quiz.models.document_quiz_models import DocumentQuizResponse
from server.app.quiz.repositories.ai_generated_quiz_repository import save_ai_generated_quiz
from server.app.quiz.repositories.live_session_repository import LiveQuizSessionRepository
from server.app.db.core.connection import (
    get_live_quiz_sessions_collection,
    get_quizzes_v2_collection,
)
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.utils.ai_generate import generate_document_quiz_with_rag
from server.app.quiz.utils.chunk_text import split_text_into_chunks
from server.app.quiz.utils.extract_text import (
    extract_text_from_bytes,
    extract_text_from_pasted_content,
)


router = APIRouter()


def _to_iso_datetime(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _format_max_size_message(max_bytes: int) -> str:
    return f"{max_bytes:,} bytes"


@router.post("/document-quizzes/generate", response_model=DocumentQuizResponse)
async def generate_document_quiz(
    question_type: str = Form(...),
    num_questions: int = Form(...),
    difficulty_level: str = Form(...),
    audience_type: str = Form(...),
    custom_instruction: str | None = Form(default=None),
    token: str | None = Form(default=None),
    document_title: str | None = Form(default=None),
    document_text: str | None = Form(default=None),
    focus_topic: str | None = Form(default=None),
    live_quiz_enabled: bool = Form(default=False),
    time_limit_minutes: int | None = Form(default=None),
    access_code_expires_at: datetime | None = Form(default=None),
    document_file: UploadFile | None = File(default=None),
    current_user=Depends(get_current_user_optional),
):
    if not document_file and not (document_text and document_text.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a PDF, DOCX, or TXT file, or paste text content.",
        )

    if document_file and document_text and document_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either an uploaded file or pasted text, not both.",
        )

    if live_quiz_enabled and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login is required to generate a live quiz access code",
        )

    if live_quiz_enabled and (not time_limit_minutes or not access_code_expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live quiz duration and access code expiration are required",
        )

    try:
        if document_file is not None:
            file_bytes = await document_file.read()
            if len(file_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded document is empty.",
                )
            if len(file_bytes) > settings.DOCUMENT_UPLOAD_MAX_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        "The uploaded document is too large. "
                        f"Maximum supported size is {_format_max_size_message(settings.DOCUMENT_UPLOAD_MAX_BYTES)}."
                    ),
                )
            document = extract_text_from_bytes(
                file_bytes=file_bytes,
                filename=document_file.filename or "document",
            )
        else:
            if len(document_text or "") > settings.DOCUMENT_TEXT_MAX_CHARS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Pasted text is too long. "
                        f"Maximum supported length is {settings.DOCUMENT_TEXT_MAX_CHARS:,} characters."
                    ),
                )
            document = extract_text_from_pasted_content(
                text=document_text or "",
                title=document_title,
            )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    chunks = split_text_into_chunks(document.text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided material is too short to generate a quiz from.",
        )

    user_id = str(current_user.id) if current_user else None
    try:
        rag_result = await generate_document_quiz_with_rag(
            document=document,
            chunks=chunks,
            question_type=question_type,
            num_questions=num_questions,
            difficulty_level=difficulty_level,
            audience_type=audience_type,
            custom_instruction=custom_instruction,
            focus_topic=focus_topic,
            user_id=user_id,
            token=token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Document quiz generation failed: {str(exc)}",
        ) from exc

    quiz_id = None
    live_access_code = None
    live_access_expires = _to_iso_datetime(access_code_expires_at)
    category_metadata = {
        "category": None,
        "category_slug": None,
        "subcategory": None,
        "subcategory_slug": None,
        "tags": [],
        "classification": None,
    }

    save_payload = {
        "profession": document.title,
        "question_type": question_type,
        "difficulty_level": difficulty_level,
        "num_questions": num_questions,
        "audience_type": audience_type,
        "custom_instruction": custom_instruction
        or f"Generated from {document.source_document_type.upper()} material.",
        "token": token,
        "questions": rag_result.questions,
        "user_id": user_id,
    }

    try:
        save_result = await save_ai_generated_quiz(save_payload)
        if save_result and "quiz_id" in save_result:
            quiz_id = save_result.get("quiz_id")
            category_metadata = {
                "category": save_result.get("category"),
                "category_slug": save_result.get("category_slug"),
                "subcategory": save_result.get("subcategory"),
                "subcategory_slug": save_result.get("subcategory_slug"),
                "tags": save_result.get("tags") or [],
                "classification": save_result.get("classification"),
            }
    except Exception:
        quiz_id = None

    if live_quiz_enabled:
        if not quiz_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Live quiz access code could not be generated because the quiz was not saved",
            )
        live_service = LiveQuizSessionService(
            LiveQuizSessionRepository(
                get_quizzes_v2_collection(),
                get_live_quiz_sessions_collection(),
            )
        )
        live_config = await live_service.generate_access_code(
            quiz_id=quiz_id,
            access_code_expires_at=access_code_expires_at,
            creator_id=user_id,
            time_limit_minutes=time_limit_minutes,
        )
        live_access_code = live_config["access_code"]
        live_access_expires = _to_iso_datetime(
            live_config.get("access_code_expires_at")
        )

    return DocumentQuizResponse(
        source="document-rag",
        questions=rag_result.questions,
        title=rag_result.title,
        description=rag_result.description,
        quiz_id=quiz_id,
        live_quiz_enabled=bool(live_access_code),
        access_code=live_access_code,
        time_limit_minutes=time_limit_minutes,
        access_code_expires_at=live_access_expires,
        source_document_type=document.source_document_type,
        source_document_name=document.source_document_name,
        source_characters=document.source_characters,
        total_source_chunks=len(chunks),
        retrieved_chunks=len(rag_result.retrieved_chunks),
        retrieval_query=rag_result.retrieval_query,
        rag_strategy=rag_result.rag_strategy,
        embedding_cache_hit=rag_result.embedding_cache_hit,
        **category_metadata,
    )
