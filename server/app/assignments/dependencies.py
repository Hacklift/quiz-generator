"""Compose assignments from the existing cohort and delivery boundaries."""

from fastapi import Depends

from server.app.assignments.repository import AssignmentRepository
from server.app.assignments.revisions import QuizRevisionRepository
from server.app.assignments.service import AssignmentService
from server.app.cohorts.dependencies import get_cohort_service
from server.app.cohorts.service import CohortService
from server.app.db.core.connection import get_quiz_revisions_collection
from server.app.quiz.routes.training_runs import get_training_run_service
from server.app.quiz.services.training_run_service import TrainingRunService


class CohortDeliveryAdapter:
    def __init__(self, service: CohortService):
        self.service = service

    async def get_cohort(self, organization_id: str, cohort_id: str):
        return await self.service.repository.get(organization_id, cohort_id)

    async def recipient_ids(self, context, cohort_id: str) -> list[str]:
        recipients = await self.service.snapshot_active_members(cohort_id, context)
        return [recipient["user_id"] for recipient in recipients]

    async def can(self, context, cohort_id: str, capability: str) -> bool:
        return await self.service.can(context, cohort_id, capability)

    async def accessible_ids(self, context, capability: str) -> list[str]:
        return await self.service.accessible_ids(context, capability)


def get_assignment_service(
    training: TrainingRunService = Depends(get_training_run_service),
    cohorts: CohortService = Depends(get_cohort_service),
    revisions_collection=Depends(get_quiz_revisions_collection),
) -> AssignmentService:
    repository = AssignmentRepository(
        training.repository,
        cohorts.users,
        cohorts.organization_memberships,
        QuizRevisionRepository(revisions_collection),
    )
    return AssignmentService(repository, training, CohortDeliveryAdapter(cohorts))
