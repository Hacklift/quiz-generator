from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.services.download_service import build_download_filename


SUPPORTED_EXPORT_FORMATS = {"txt", "json", "pdf", "docx"}


async def quiz_export_link(quiz_id: str, format: str = "pdf") -> dict[str, str]:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    file_format = format.lower().strip()
    if file_format not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {format}")

    quiz = await QuizV2Repository(get_quizzes_v2_collection()).find_by_id(quiz_id)
    if quiz is None:
        raise ValueError("Quiz not found")
    if quiz.owner_user_id and quiz.owner_user_id != context.user_id:
        visibility = quiz.visibility.value if hasattr(quiz.visibility, "value") else str(quiz.visibility)
        if visibility not in {"public", "unlisted"}:
            raise PermissionError("Quiz access is required to export this quiz.")

    return {
        "action_id": f"quiz_export:{quiz_id}:{file_format}",
        "quiz_id": quiz_id,
        "format": file_format,
        "href": "/download-quiz",
        "filename": build_download_filename(quiz.title, file_format),
    }
