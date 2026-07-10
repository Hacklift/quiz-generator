from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService


async def library_list_saved_quizzes(limit: int = 100) -> list[dict]:
    context = await get_mcp_request_context(require_auth=True)
    return await QuizUserLibraryService().list_saved_quizzes(
        user_id=context.user_id,
        limit=limit,
    )


async def library_get_saved_quiz(saved_quiz_id: str) -> dict | None:
    context = await get_mcp_request_context(require_auth=True)
    return await QuizUserLibraryService().get_saved_quiz(
        user_id=context.user_id,
        saved_quiz_id=saved_quiz_id,
    )


async def library_find_saved_quiz_by_title(title: str, limit: int = 10) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    return await QuizUserLibraryService().find_saved_quiz_by_title(
        user_id=context.user_id,
        title=title,
        limit=limit,
    )


async def library_list_history(limit: int = 100) -> list[dict]:
    context = await get_mcp_request_context(require_auth=True)
    return await QuizUserLibraryService().list_quiz_history_items(
        user_id=context.user_id,
        limit=limit,
    )


async def library_get_history_detail(history_id: str) -> dict | None:
    context = await get_mcp_request_context(require_auth=True)
    detail = await QuizUserLibraryService().get_quiz_history_detail(
        user_id=context.user_id,
        history_id=history_id,
    )
    return detail.model_dump(mode="json") if detail else None


async def library_save_quiz(
    title: str | None = None,
    question_type: str | None = None,
    questions: list[dict] | None = None,
    quiz_id: str | None = None,
) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    saved_quiz = await QuizUserLibraryService().create_saved_quiz(
        user_id=context.user_id,
        title=title,
        question_type=question_type,
        questions=questions,
        quiz_id=quiz_id,
    )
    return {
        "id": str(saved_quiz.id),
        "saved_quiz_id": str(saved_quiz.id),
        "quiz_id": saved_quiz.quiz_id,
        "title": saved_quiz.display_title,
        "saved_at": saved_quiz.saved_at.isoformat(),
    }


async def saved_quiz_rename(saved_quiz_id: str, title: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    renamed = await QuizUserLibraryService().rename_saved_quiz(
        user_id=context.user_id,
        saved_quiz_id=saved_quiz_id,
        title=title,
    )
    if renamed is None:
        raise ValueError("Saved quiz not found")
    return renamed.model_dump(mode="json")


async def saved_quiz_delete(saved_quiz_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    deleted = await QuizUserLibraryService().delete_saved_quiz(
        user_id=context.user_id,
        saved_quiz_id=saved_quiz_id,
    )
    if not deleted:
        raise ValueError("Saved quiz not found")
    return {
        "message": "Saved quiz deleted.",
        "saved_quiz_id": saved_quiz_id,
        "deleted": True,
    }
