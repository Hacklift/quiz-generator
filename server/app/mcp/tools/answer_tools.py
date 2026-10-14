from server.app.mcp.auth import get_mcp_request_context
from server.app.quiz.services.quiz_answer_service import QuizAnswerKeyService


async def quiz_get_answers(quiz_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True, require_verified=True)
    if context.tenant_id is None:
        raise PermissionError("Organization context is required to read quiz answers.")
    if not str(quiz_id or "").strip():
        raise ValueError("quiz_id is required.")
    return await QuizAnswerKeyService().get_answer_key(
        user_id=context.user_id,
        quiz_id=quiz_id,
        organization_id=context.tenant_id,
    )
