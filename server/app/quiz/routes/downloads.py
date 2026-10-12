import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from server.app.core.dependencies import get_current_user_optional
from server.app.db.core.connection import (
    get_organization_memberships_collection,
    get_organizations_collection,
    get_quizzes_v2_collection,
    get_user_sessions_collection,
)
from server.app.organizations.dependencies import resolve_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.policy import (
    OrganizationAction,
    require_organization_permission,
)
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.core.rate_limiter import limiter
from server.app.quiz.schemas.download_query import DownloadQuizQuery
from server.app.quiz.schemas.download_schemas import DownloadQuizRequestModel
from server.app.quiz.services.download_service import (
    download_mock_quiz,
    download_quiz_by_id,
    download_quiz_from_payload,
)
from server.app.users.models import UserOut


logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_download_organization(
    current_user: UserOut,
    *,
    sessions_collection,
    organizations_collection,
    memberships_collection,
) -> OrganizationContext:
    """Resolve tenant authority only for downloads of stored tenant content.

    Generated sample downloads are intentionally usable without tenant state.
    Resolving scope inside the persisted-quiz branch prevents a stale
    authenticated session from blocking that non-tenant capability.
    """
    if not current_user.session_id:
        raise HTTPException(status_code=401, detail="Session context is missing")
    return await resolve_active_organization_context(
        current_user=current_user,
        principal=OrganizationPrincipal(
            user_id=current_user.id,
            session_id=current_user.session_id,
            platform_role=current_user.role or "user",
        ),
        sessions_collection=sessions_collection,
        organizations_collection=organizations_collection,
        memberships_collection=memberships_collection,
    )


@router.get("/download-quiz")
@limiter.limit("20/minute")
async def download_quiz_handler(
    request: Request,
    response: Response,
    query: DownloadQuizQuery = Depends(),
    current_user: UserOut | None = Depends(get_current_user_optional),
    sessions_collection=Depends(get_user_sessions_collection),
    organizations_collection=Depends(get_organizations_collection),
    memberships_collection=Depends(get_organization_memberships_collection),
) -> StreamingResponse:
    logger.info("Received download query: %s", query)
    if query.quiz_id:
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not current_user.is_verified:
            raise HTTPException(status_code=403, detail="Email not verified")
        organization = await _resolve_download_organization(
            current_user,
            sessions_collection=sessions_collection,
            organizations_collection=organizations_collection,
            memberships_collection=memberships_collection,
        )
        quiz = await QuizV2Repository(get_quizzes_v2_collection()).find_by_id_for_organization(
            query.quiz_id,
            organization.organization_id,
        )
        if quiz is None:
            raise HTTPException(status_code=404, detail="Quiz not found")
        require_organization_permission(
            context=organization,
            action=OrganizationAction.CONTENT_EXPORT,
            resource=quiz.model_dump(by_alias=True),
        )
        return await download_quiz_by_id(
            quiz_id=query.quiz_id,
            file_format=query.format,
            organization_id=organization.organization_id,
        )

    return download_mock_quiz(query.format, query.question_type, query.num_question)


@router.post("/download-quiz")
@limiter.limit("20/minute")
async def download_quiz_from_payload_handler(
    request: Request,
    response: Response,
    payload: DownloadQuizRequestModel = Body(...),
) -> StreamingResponse:
    return download_quiz_from_payload(
        title=payload.title,
        description=payload.description,
        quiz_type=payload.quiz_type,
        questions=[
            question.model_dump(exclude_none=True)
            for question in payload.questions
        ],
        file_format=payload.format,
    )
