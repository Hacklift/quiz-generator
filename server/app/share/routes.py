from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import logging
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.core.dependencies import get_current_user, get_current_user_optional
from server.app.organizations.dependencies import (
    get_active_organization_context,
    resolve_active_organization_context,
)
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.policy import (
    OrganizationAction,
    require_organization_permission,
)
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.core.rate_limiter import limiter
from server.app.db.core.connection import (
    get_organization_memberships_collection,
    get_organizations_collection,
    get_quizzes_v2_collection,
    get_user_sessions_collection,
)
from server.app.quiz.schemas.quiz_schemas import QuizSchema
from server.app.share.services import SharedQuizReadService
from server.app.share.schemas import (
    ShareEmailRequest,
    ShareEmailResponse,
    ShareQuizResponse,
    SharedQuizDataResponse,
)
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService
from server.app.users.models import UserOut


logger = logging.getLogger(__name__)

load_dotenv()

share_url = os.getenv("SHARE_URL")

if not share_url:
    raise EnvironmentError("[Config Error] 'SHARE_URL' is not defined in environment")


router = APIRouter()
shared_quiz_read_service = SharedQuizReadService()


@router.get("/get-quiz-id", response_model=QuizSchema)
async def get_random_quiz_id(
    quizzes_v2_collection: AsyncIOMotorCollection = Depends(get_quizzes_v2_collection),
):
    try:
        # Only curated seed quizzes are eligible: user-generated quizzes must
        # never be handed out to anonymous callers.
        quiz_list = await quizzes_v2_collection.aggregate([
            {"$match": {"status": {"$ne": "deleted"}, "source": "seed"}},
            {"$sample": {"size": 1}},
        ]).to_list(length=1)
        if not quiz_list:
            raise HTTPException(detail="Unable to fetch from database!", status_code=404)
        selected_quiz = quiz_list[0]
        return QuizSchema(
            id=str(selected_quiz["_id"]),
            title=selected_quiz["title"],
            description=selected_quiz.get("description"),
            quiz_type=selected_quiz["quiz_type"],
            owner_id=selected_quiz.get("owner_user_id"),
            canonical_quiz_id=str(selected_quiz["_id"]),
            created_at=selected_quiz["created_at"],
            updated_at=selected_quiz["updated_at"],
            questions=selected_quiz["questions"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("Error occured while fetching quiz from database: %s", exc)
        raise HTTPException(detail="Unable to fetch from database!", status_code=404)


async def _require_share_permission(
    quiz_id: str,
    organization: OrganizationContext,
) -> object:
    quiz = await QuizV2Repository(get_quizzes_v2_collection()).find_by_id_for_organization(
        quiz_id,
        organization.organization_id,
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    require_organization_permission(
        context=organization,
        action=OrganizationAction.CONTENT_SHARE,
        resource=quiz.model_dump(by_alias=True),
    )
    return quiz


async def _is_anonymously_shareable(quiz_id: str) -> bool:
    """Check the same explicit public capability used by the shared view.

    Link creation is safe without authentication only when following that link
    already grants anonymous read access. Private tenant content therefore
    never becomes shareable merely because a caller knows its identifier.
    """
    return bool(await shared_quiz_read_service.resolve_shared_quiz(quiz_id))


async def _resolve_share_organization(
    current_user: UserOut,
    *,
    sessions_collection,
    organizations_collection,
    memberships_collection,
) -> OrganizationContext:
    """Resolve tenant state only after a link is known not to be public.

    FastAPI resolves dependencies before entering the route. Keeping this
    explicit prevents a stale authenticated tenant selection from blocking an
    otherwise valid public link, while private resources still require a
    current, server-proven membership.
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


@router.get("/share-quiz/{quiz_id}", response_model=ShareQuizResponse)
async def get_share_link(
    quiz_id: str,
    current_user: UserOut | None = Depends(get_current_user_optional),
    sessions_collection=Depends(get_user_sessions_collection),
    organizations_collection=Depends(get_organizations_collection),
    memberships_collection=Depends(get_organization_memberships_collection),
):
    try:
        # Public and unlisted quizzes carry an explicit anonymous-read
        # capability. Guests may copy their link; no tenant resource is
        # exposed that was not already readable through the resulting URL.
        if await _is_anonymously_shareable(quiz_id):
            shareable_link = f"{share_url}/share/{quiz_id}"
            logger.info("shareable link generated successfully")
            return {"link": shareable_link}

        if current_user is None:
            raise HTTPException(status_code=404, detail="Quiz not found")

        organization = await _resolve_share_organization(
            current_user,
            sessions_collection=sessions_collection,
            organizations_collection=organizations_collection,
            memberships_collection=memberships_collection,
        )

        # Preserve the distinction between a cross-organization identifier
        # (404) and an in-organization role denial (403).
        await _require_share_permission(quiz_id, organization)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz must be public or unlisted before it can be shared by link",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("Unable to generate shareable link: %s", exc)
        raise HTTPException(detail="Failed to generate shareable link", status_code=500)


@router.get("/shared-quiz/{quiz_id}", response_model=SharedQuizDataResponse)
async def get_shared_quiz_data(quiz_id: str):
    try:
        shared_quiz = await shared_quiz_read_service.resolve_shared_quiz(quiz_id)
        if not shared_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return shared_quiz
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unable to fetch shared quiz data for %s: %s", quiz_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch shared quiz data.",
        )


@router.post("/share-email", response_model=ShareEmailResponse)
@limiter.limit("5/hour")
async def share_quiz_via_email(
    request: Request,
    response: Response,
    query: ShareEmailRequest,
    email_svc: EmailService = Depends(get_email_service),
    current_user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    try:
        await _require_share_permission(query.quiz_id, organization)
        shared_quiz = await shared_quiz_read_service.resolve_shared_quiz(query.quiz_id)
        if not shared_quiz:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Quiz must be public or unlisted before it can be shared by email",
            )

        await email_svc.send_email(
            to=query.recipient_email,
            template_id="quiz_link",
            template_vars={
                "title": shared_quiz["title"],
                "description": shared_quiz["description"],
                # Always build the link server-side; never trust a client URL.
                "link": f"{share_url}/share/{query.quiz_id}",
            },
            purpose="quiz_link",
            priority="default",
        )
        logger.info("[API] Share email pipeline triggered for %s and quiz ID %s", query.recipient_email, query.quiz_id)
        return {"message": "Email sent successfully!"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[API Error] Share email pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again later.",
        )
