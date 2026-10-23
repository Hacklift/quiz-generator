from fastapi import HTTPException

from server.app.db.core.connection import get_organizations_collection
from server.app.organizations.models import OrganizationContext
from server.app.organizations.policy import (
    OrganizationAction,
    OrganizationPolicy,
    require_organization_permission,
)
from server.app.organizations.repository import OrganizationRepository
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2


class QuizPracticeAccess:
    """Apply content policy to practice and optional history-source enrichment."""

    def __init__(self, organizations: OrganizationRepository | None = None):
        self.organizations = organizations or OrganizationRepository(get_organizations_collection())

    async def require_readable(
        self, quiz: QuizDocumentV2, organization: OrganizationContext | None,
    ) -> None:
        if quiz.visibility.value in {"public", "unlisted"}:
            if await self.organizations.get_active(quiz.organization_id) is None:
                raise HTTPException(status_code=404, detail="Quiz not found")
            return
        if organization is None:
            raise HTTPException(status_code=404, detail="Quiz not found")
        require_organization_permission(
            context=organization, action=OrganizationAction.CONTENT_READ,
            resource=quiz.model_dump(by_alias=True),
        )

    async def readable_sources(
        self, quizzes: list[QuizDocumentV2], organization: OrganizationContext | None,
    ) -> list[QuizDocumentV2]:
        # Historical result snapshots remain readable even when their source
        # quiz is no longer accessible. Do not enrich them with private data.
        public_organization_ids = {
            quiz.organization_id for quiz in quizzes
            if quiz.visibility.value in {"public", "unlisted"}
        }
        public_organizations = {
            str(organization["_id"])
            for organization in await self.organizations.list_active_by_ids(
                list(public_organization_ids)
            )
        } if public_organization_ids else set()
        readable = []
        policy = OrganizationPolicy()
        for quiz in quizzes:
            if quiz.visibility.value in {"public", "unlisted"}:
                if quiz.organization_id in public_organizations:
                    readable.append(quiz)
            elif organization is not None and policy.can(
                organization.principal, OrganizationAction.CONTENT_READ,
                quiz.model_dump(by_alias=True), organization,
            ):
                readable.append(quiz)
        return readable
