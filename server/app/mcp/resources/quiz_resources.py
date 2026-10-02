from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.mcp.auth import get_mcp_request_context
from server.app.organizations.policy import (
    OrganizationAction,
    require_organization_permission,
)
from server.app.mcp.tools.share_tools import share_get_quiz
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository


async def quiz_resource(quiz_id: str) -> dict | None:
    context = await get_mcp_request_context()
    repository = QuizV2Repository(get_quizzes_v2_collection())
    if context.organization_context is not None:
        quiz = await repository.find_by_id_for_organization(
            quiz_id,
            context.organization_context.organization_id,
        )
        if quiz is None:
            return None
        require_organization_permission(
            context=context.organization_context,
            action=OrganizationAction.CONTENT_READ,
            resource=quiz.model_dump(by_alias=True),
        )
    else:
        quiz = await repository.find_public_shareable_by_id(quiz_id)
        if quiz is None:
            return None
    return quiz.model_dump(mode="json", by_alias=True)


async def shared_quiz_resource(quiz_id: str) -> dict | None:
    return await share_get_quiz(quiz_id)
