from uuid import uuid4

from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.mcp.auth import get_mcp_request_context
from server.app.organizations.policy import (
    OrganizationAction,
    require_organization_permission,
)
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.services.download_service import build_download_filename


SUPPORTED_EXPORT_FORMATS = {"txt", "json", "pdf", "docx"}


async def quiz_export_link(quiz_id: str, format: str = "pdf") -> dict[str, str]:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    file_format = format.lower().strip()
    if file_format not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {format}")

    if context.organization_context is None:
        raise PermissionError("Organization context is required to export a quiz.")
    quiz = await QuizV2Repository(get_quizzes_v2_collection()).find_by_id_for_organization(
        quiz_id,
        context.organization_context.organization_id,
    )
    if quiz is None:
        raise ValueError("Quiz not found")
    require_organization_permission(
        context=context.organization_context,
        action=OrganizationAction.CONTENT_EXPORT,
        resource=quiz.model_dump(by_alias=True),
    )

    return {
        "action_id": f"quiz_export:{quiz_id}:{file_format}:{uuid4()}",
        "quiz_id": quiz_id,
        "format": file_format,
        "href": "/download-quiz",
        "filename": build_download_filename(quiz.title, file_format),
    }
