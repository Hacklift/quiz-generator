from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.mcp.auth import get_mcp_request_context
from server.app.mcp.tools.share_tools import share_get_quiz
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository


async def quiz_resource(quiz_id: str) -> dict | None:
    quiz = await QuizV2Repository(get_quizzes_v2_collection()).find_by_id(quiz_id)
    if quiz is None:
        return None
    visibility = quiz.visibility.value if hasattr(quiz.visibility, "value") else str(quiz.visibility)
    if visibility not in {"public", "unlisted"}:
        context = await get_mcp_request_context()
        if not context.is_authenticated or quiz.owner_user_id != context.user_id:
            raise PermissionError("Authentication or quiz ownership is required to read this quiz.")
    return quiz.model_dump(mode="json", by_alias=True)


async def shared_quiz_resource(quiz_id: str) -> dict | None:
    return await share_get_quiz(quiz_id)
