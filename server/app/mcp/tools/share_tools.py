from server.app.core.config import settings
from server.app.email_platform.service import build_email_service
from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.share.services import SharedQuizReadService


async def share_get_quiz(quiz_id: str) -> dict | None:
    return await SharedQuizReadService().resolve_shared_quiz(quiz_id)


async def share_create_link(quiz_id: str) -> dict[str, str]:
    quiz = await QuizV2Repository(get_quizzes_v2_collection()).find_by_id(quiz_id)
    if quiz is None:
        raise ValueError("Quiz not found")
    visibility = quiz.visibility.value if hasattr(quiz.visibility, "value") else str(quiz.visibility)
    if visibility not in {"public", "unlisted"}:
        context = await get_mcp_request_context(require_auth=True)
        if quiz.owner_user_id != context.user_id:
            raise PermissionError("Quiz ownership is required to create a share link.")
    return {"link": f"{settings.share_url}/share/{quiz_id}"}


async def share_send_email(
    quiz_id: str,
    recipient_email: str,
    shareable_link: str | None = None,
) -> dict[str, str]:
    await get_mcp_request_context(require_auth=True, require_verified=True)
    shared_quiz = await SharedQuizReadService().resolve_shared_quiz(quiz_id)
    if not shared_quiz:
        raise ValueError("Quiz not found")

    link = shareable_link or f"{settings.share_url}/share/{quiz_id}"
    email_service = build_email_service(None)
    await email_service.send_email(
        to=recipient_email,
        template_id="quiz_link",
        template_vars={
            "title": shared_quiz["title"],
            "description": shared_quiz["description"],
            "link": link,
        },
        purpose="quiz_link",
        priority="default",
    )
    return {
        "message": "Email sent successfully.",
        "quiz_id": quiz_id,
        "recipient_email": recipient_email,
        "link": link,
    }
