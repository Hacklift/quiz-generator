from fastapi import Depends

from server.app.cohorts.repository import CohortRepository
from server.app.cohorts.service import CohortService
from server.app.db.core.connection import (
    get_cohorts_collection, get_cohort_memberships_collection,
    get_organization_memberships_collection, get_users_collection,
)


def get_cohort_service(
    cohorts_collection=Depends(get_cohorts_collection),
    cohort_memberships_collection=Depends(get_cohort_memberships_collection),
    organization_memberships_collection=Depends(get_organization_memberships_collection),
    users_collection=Depends(get_users_collection),
) -> CohortService:
    return CohortService(
        CohortRepository(cohorts_collection, cohort_memberships_collection),
        organization_memberships_collection, users_collection,
    )
