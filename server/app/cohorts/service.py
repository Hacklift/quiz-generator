from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import HTTPException

from server.app.cohorts.models import CohortDocument, CohortMembershipDocument
from server.app.cohorts.repository import CohortRepository, cursor_object_id, page_result
from server.app.cohorts.schemas import (
    CohortMemberOption, CohortMemberOptionsResponse, CohortMemberPageResponse,
    CohortMemberResponse, CohortPageResponse, CohortResponse, CreateCohortRequest,
    SetCohortMemberRequest, UpdateCohortRequest,
)
from server.app.organizations.models import OrganizationContext
from server.app.organizations.policy import (
    OrganizationAction, OrganizationPolicy, require_organization_permission,
)

MAX_COHORT_RECIPIENTS = 1000


class CohortService:
    def __init__(self, repository: CohortRepository, organization_memberships_collection, users_collection):
        self.repository = repository
        self.organization_memberships = organization_memberships_collection
        self.users = users_collection
        self.policy = OrganizationPolicy()

    async def _context(self, context: OrganizationContext) -> OrganizationContext:
        membership = await self.organization_memberships.find_one({
            "organization_id": context.organization_id,
            "user_id": context.principal.user_id, "status": "active",
        })
        if membership is None:
            raise HTTPException(403, "Organization access denied")
        return context.model_copy(update={"membership_role": membership["role"], "membership": membership})

    @staticmethod
    def _require(context, action, resource):
        require_organization_permission(context=context, action=action, resource=resource)

    async def _load(self, cohort_id: str, context: OrganizationContext) -> dict:
        cohort = await self.repository.get(context.organization_id, cohort_id)
        if cohort is None:
            raise HTTPException(404, "Cohort not found")
        return cohort

    async def _resource(self, cohort: dict, context: OrganizationContext) -> dict:
        member = await self.repository.get_membership(
            context.organization_id, str(cohort["_id"]), context.principal.user_id,
        )
        return {**cohort, "cohort_id": str(cohort["_id"]), "cohort_membership": member}

    async def policy_resource(self, cohort_id: str, context: OrganizationContext) -> dict[str, Any]:
        """Trusted delegation facts for assignment/reporting policy decisions.

        Callers must apply their specific action to the returned resource; read
        membership alone is deliberately not assignment/report authorization.
        Archived cohorts remain readable for retained assignment evidence.
        """
        context = await self._context(context)
        resource = await self._resource(await self._load(cohort_id, context), context)
        self._require(context, OrganizationAction.COHORT_READ, resource)
        return resource

    @staticmethod
    def _capability_action(capability: str) -> OrganizationAction:
        actions = {
            "read": OrganizationAction.COHORT_READ,
            "manage": OrganizationAction.COHORT_MANAGE,
            # Existing delivery may still be closed after cohort archival.
            # Creation and roster snapshots independently require active status.
            "assign": OrganizationAction.ASSIGNMENT_MANAGE,
            "report": OrganizationAction.COHORT_REPORT,
            "attempt": OrganizationAction.MEMBER_ATTEMPT_READ,
        }
        if capability not in actions:
            raise ValueError("Unknown cohort capability")
        return actions[capability]

    async def can(self, context: OrganizationContext, cohort_id: str, capability: str) -> bool:
        """Authorize a cohort capability using current organization membership."""
        return await self.can_for_cohort(cohort_id, context, self._capability_action(capability))

    async def can_for_cohort(self, cohort_id: str, context: OrganizationContext, action: OrganizationAction) -> bool:
        try:
            context = await self._context(context)
            resource = await self._resource(await self._load(cohort_id, context), context)
        except HTTPException as exc:
            if exc.status_code in {403, 404}:
                return False
            raise
        return self.policy.can(context.principal, action, resource, context)

    async def accessible_ids(self, context: OrganizationContext, capability: str) -> list[str]:
        """Bounded delegation IDs for assignment list filters; never truncate."""
        return await self.scoped_accessible_ids(context, self._capability_action(capability))

    async def scoped_accessible_ids(self, context: OrganizationContext, action: OrganizationAction, *, limit: int = MAX_COHORT_RECIPIENTS) -> list[str]:
        if not 1 <= limit <= MAX_COHORT_RECIPIENTS:
            raise HTTPException(422, "Delegated cohort limit must be between 1 and 1000")
        context = await self._context(context)
        tenant_wide = self.policy.can(
            context.principal, action, {"organization_id": context.organization_id}, context,
        )
        if not tenant_wide and action in {
            OrganizationAction.COHORT_MANAGE, OrganizationAction.COHORT_MEMBERSHIP_MANAGE,
        }:
            return []
        query: dict[str, Any] = {"organization_id": context.organization_id}
        if action == OrganizationAction.ASSIGNMENT_CREATE:
            query["status"] = "active"
        pipeline = [{"$match": query}, {"$sort": {"_id": 1}}]
        if not tenant_wide:
            member_query: dict[str, Any] = {
                "organization_id": context.organization_id, "user_id": context.principal.user_id,
                "status": "active", "$expr": {"$eq": ["$cohort_id", "$$cohort"]},
            }
            if action in {
                OrganizationAction.ASSIGNMENT_CREATE, OrganizationAction.ASSIGNMENT_MANAGE,
                OrganizationAction.COHORT_REPORT, OrganizationAction.MEMBER_ATTEMPT_READ,
            }:
                member_query.update({
                    "role": "facilitator",
                    "can_assign" if action in {
                        OrganizationAction.ASSIGNMENT_CREATE, OrganizationAction.ASSIGNMENT_MANAGE,
                    } else "can_report": True,
                })
            pipeline.extend([
                {"$lookup": {
                    "from": self.repository.memberships.name,
                    "let": {"cohort": {"$toString": "$_id"}},
                    "pipeline": [{"$match": member_query}, {"$limit": 1}],
                    "as": "_membership",
                }}, {"$match": {"_membership.0": {"$exists": True}}},
            ])
        pipeline.append({"$limit": limit + 1})
        rows = await self.repository.cohorts.aggregate(pipeline).to_list(length=limit + 1)
        if len(rows) > limit:
            raise HTTPException(413, "Too many delegated cohorts; filter by a specific cohort")
        return [str(row["_id"]) for row in rows if self.policy.can(
            context.principal, action, {
                **row, "cohort_id": str(row["_id"]),
                "cohort_membership": (row.get("_membership") or [None])[0],
            }, context,
        )]

    def _response(self, resource: dict, context: OrganizationContext) -> CohortResponse:
        return CohortResponse(
            id=str(resource["_id"]),
            **{key: resource[key] for key in (
                "organization_id", "kind", "name", "parent_cohort_id", "status",
                "created_by_user_id", "created_at", "updated_at",
            )},
            can_manage=self.policy.can(context.principal, OrganizationAction.COHORT_MANAGE, resource, context),
            can_assign=self.policy.can(context.principal, OrganizationAction.ASSIGNMENT_CREATE, resource, context),
            can_report=self.policy.can(context.principal, OrganizationAction.COHORT_REPORT, resource, context),
        )

    async def _validate_parent(self, parent_id: str | None, cohort_id: str | None, context: OrganizationContext) -> None:
        if parent_id is None:
            return
        if parent_id == cohort_id:
            raise HTTPException(409, "A cohort cannot be its own parent")
        parent = await self._load(parent_id, context)
        if parent["status"] != "active":
            raise HTTPException(409, "Parent cohort is archived")
        if parent.get("parent_cohort_id") is not None:
            raise HTTPException(409, "Cohorts support only one parent level")
        if cohort_id and await self.repository.has_children(context.organization_id, cohort_id):
            raise HTTPException(409, "A cohort with retained children cannot become a child")

    async def create_cohort(self, payload: CreateCohortRequest, context: OrganizationContext) -> CohortResponse:
        context = await self._context(context)
        self._require(context, OrganizationAction.COHORT_MANAGE, None)
        async with self.repository.hierarchy_mutation(context.organization_id) as token:
            await self._validate_parent(payload.parent_cohort_id, None, context)
            row = await self.repository.create(CohortDocument(
                organization_id=context.organization_id, created_by_user_id=context.principal.user_id,
                **payload.model_dump(),
            ), token=token)
        return self._response({**row, "cohort_id": str(row["_id"])}, context)

    async def get_cohort(self, cohort_id: str, context: OrganizationContext) -> CohortResponse:
        context = await self._context(context)
        row = await self._resource(await self._load(cohort_id, context), context)
        self._require(context, OrganizationAction.COHORT_READ, row)
        return self._response(row, context)

    async def list_cohorts(self, context: OrganizationContext, *, limit: int = 50, cursor: str | None = None, status: str | None = "active") -> CohortPageResponse:
        context = await self._context(context)
        self._page_size(limit)
        if status is not None and status not in {"active", "archived"}:
            raise HTTPException(422, "Invalid cohort status")
        tenant_wide = self.policy.can(context.principal, OrganizationAction.COHORT_READ, None, context)
        rows, next_cursor = await self.repository.list_page(
            context.organization_id, limit=limit, cursor=cursor, status=status,
            user_id=None if tenant_wide else context.principal.user_id,
        )
        cohort_ids = [str(row["_id"]) for row in rows]
        memberships = await self.repository.memberships.find({
            "organization_id": context.organization_id, "user_id": context.principal.user_id,
            "cohort_id": {"$in": cohort_ids}, "status": "active",
        }).to_list(length=len(cohort_ids)) if cohort_ids else []
        by_cohort = {row["cohort_id"]: row for row in memberships}
        return CohortPageResponse(items=[self._response({
            **row, "cohort_id": str(row["_id"]), "cohort_membership": by_cohort.get(str(row["_id"])),
        }, context) for row in rows], next_cursor=next_cursor)

    async def update_cohort(self, cohort_id: str, payload: UpdateCohortRequest, context: OrganizationContext) -> CohortResponse:
        context = await self._context(context)
        self._require(context, OrganizationAction.COHORT_MANAGE, await self._load(cohort_id, context))
        async with self.repository.hierarchy_mutation(context.organization_id) as token:
            row = await self._load(cohort_id, context)
            cohort_id = str(row["_id"])
            self._require(context, OrganizationAction.COHORT_MANAGE, row)
            if row["status"] != "active":
                raise HTTPException(409, "Archived cohorts cannot be edited")
            changes = payload.model_dump(exclude_unset=True)
            await self._validate_parent(changes.get("parent_cohort_id", row.get("parent_cohort_id")), cohort_id, context)
            if changes:
                row = await self.repository.update(context.organization_id, cohort_id, changes, token=token)
                if row is None:
                    raise HTTPException(409, "Cohort changed; refresh before retrying")
        return self._response({**row, "cohort_id": cohort_id}, context)

    async def archive_cohort(self, cohort_id: str, context: OrganizationContext) -> CohortResponse:
        context = await self._context(context)
        self._require(context, OrganizationAction.COHORT_MANAGE, await self._load(cohort_id, context))
        async with self.repository.hierarchy_mutation(context.organization_id) as token:
            row = await self._load(cohort_id, context)
            cohort_id = str(row["_id"])
            self._require(context, OrganizationAction.COHORT_MANAGE, row)
            if row["status"] == "active":
                if await self.repository.has_active_children(context.organization_id, cohort_id):
                    raise HTTPException(409, "Archive or move child cohorts first")
                row = await self.repository.update(context.organization_id, cohort_id, {"status": "archived"}, token=token)
                if row is None:
                    raise HTTPException(409, "Cohort changed; refresh before retrying")
        return self._response({**row, "cohort_id": cohort_id}, context)

    async def _users_by_id(self, user_ids: list[str]) -> dict[str, dict]:
        ids = [ObjectId(value) for value in user_ids if ObjectId.is_valid(value)]
        if not ids:
            return {}
        rows = await self.users.find(
            {"_id": {"$in": ids}, "status": {"$ne": "deleted"}},
            {"full_name": 1, "username": 1, "email": 1},
        ).to_list(length=len(ids))
        return {str(row["_id"]): row for row in rows}

    @staticmethod
    def _display_name(user: dict | None) -> str:
        return (user or {}).get("full_name") or (user or {}).get("username") or "Member"

    @staticmethod
    def _page_size(limit: int) -> None:
        if not 1 <= limit <= 100:
            raise HTTPException(422, "Page size must be between 1 and 100")

    async def list_members(self, cohort_id: str, context: OrganizationContext, *, limit: int = 50, cursor: str | None = None) -> CohortMemberPageResponse:
        context = await self._context(context)
        self._page_size(limit)
        resource = await self._resource(await self._load(cohort_id, context), context)
        self._require(context, OrganizationAction.COHORT_READ, resource)
        cohort_id = resource["cohort_id"]
        rows, next_cursor = await self.repository.list_members_page(
            context.organization_id, cohort_id, limit=limit, cursor=cursor,
            organization_memberships_collection=self.organization_memberships,
        )
        users = await self._users_by_id([row["user_id"] for row in rows])
        return CohortMemberPageResponse(items=[CohortMemberResponse(
            user_id=row["user_id"], role=row["role"], name=self._display_name(users.get(row["user_id"])),
            can_assign=row["can_assign"], can_report=row["can_report"],
        ) for row in rows], next_cursor=next_cursor)

    async def set_member(self, cohort_id: str, payload: SetCohortMemberRequest, context: OrganizationContext) -> CohortMemberResponse:
        context = await self._context(context)
        self._require(context, OrganizationAction.COHORT_MEMBERSHIP_MANAGE, await self._load(cohort_id, context))
        async with self.repository.hierarchy_mutation(context.organization_id) as token:
            cohort = await self._load(cohort_id, context)
            cohort_id = str(cohort["_id"])
            self._require(context, OrganizationAction.COHORT_MEMBERSHIP_MANAGE, cohort)
            if cohort["status"] != "active":
                raise HTTPException(409, "Archived cohort membership cannot be edited")
            member = await self.organization_memberships.find_one({
                "organization_id": context.organization_id, "user_id": payload.user_id, "status": "active",
            })
            users = await self._users_by_id([payload.user_id])
            if member is None or payload.user_id not in users:
                raise HTTPException(404, "Active organization member not found")
            row = await self.repository.set_member(CohortMembershipDocument(
                organization_id=context.organization_id, cohort_id=cohort_id,
                created_by_user_id=context.principal.user_id, **payload.model_dump(),
            ), token=token)
        return CohortMemberResponse(
            user_id=row["user_id"], role=row["role"], name=self._display_name(users[payload.user_id]),
            can_assign=row["can_assign"], can_report=row["can_report"],
        )

    async def remove_member(self, cohort_id: str, user_id: str, context: OrganizationContext) -> None:
        context = await self._context(context)
        self._require(context, OrganizationAction.COHORT_MEMBERSHIP_MANAGE, await self._load(cohort_id, context))
        async with self.repository.hierarchy_mutation(context.organization_id) as token:
            cohort = await self._load(cohort_id, context)
            cohort_id = str(cohort["_id"])
            self._require(context, OrganizationAction.COHORT_MEMBERSHIP_MANAGE, cohort)
            if cohort["status"] != "active":
                raise HTTPException(409, "Archived cohort membership cannot be edited")
            if not ObjectId.is_valid(user_id):
                raise HTTPException(404, "Cohort member not found")
            user_id = str(ObjectId(user_id))
            await self.repository.remove_member(context.organization_id, cohort_id, user_id, token=token)

    async def member_options(self, context: OrganizationContext, *, limit: int = 50, cursor: str | None = None) -> CohortMemberOptionsResponse:
        context = await self._context(context)
        self._require(context, OrganizationAction.COHORT_MEMBERSHIP_MANAGE, None)
        self._page_size(limit)
        query: dict[str, Any] = {"organization_id": context.organization_id, "status": "active"}
        object_id = cursor_object_id(cursor)
        if object_id is not None:
            query["_id"] = {"$lt": object_id}
        rows = await self.organization_memberships.aggregate([
            {"$match": query}, {"$sort": {"_id": -1}},
            {"$lookup": {
                "from": self.users.name, "let": {"user_object_id": {"$convert": {
                    "input": "$user_id", "to": "objectId", "onError": None, "onNull": None,
                }}},
                "pipeline": [{"$match": {
                    "status": {"$ne": "deleted"},
                    "$expr": {"$eq": ["$_id", "$$user_object_id"]},
                }}, {"$project": {"full_name": 1, "username": 1}}], "as": "_user",
            }}, {"$match": {"_user.0": {"$exists": True}}}, {"$limit": limit + 1},
        ]).to_list(length=limit + 1)
        page, next_cursor = page_result(rows, limit)
        return CohortMemberOptionsResponse(items=[CohortMemberOption(
            user_id=row["user_id"], name=self._display_name(row["_user"][0]),
        ) for row in page], next_cursor=next_cursor)

    async def snapshot_active_members(self, cohort_id: str, context: OrganizationContext, *, limit: int = MAX_COHORT_RECIPIENTS) -> list[dict[str, str]]:
        """Snapshot only learner/member recipients, never facilitators/guardians.

        Returns user_id/email/name/cohort_id for durable assignment provisioning.
        The fixed upper bound is enforced, not silently truncated or caller-raised.
        Existing assignments must retain this roster instead of querying it again.
        """
        if not 1 <= limit <= MAX_COHORT_RECIPIENTS:
            raise HTTPException(422, "Recipient snapshot limit must be between 1 and 1000")
        context = await self._context(context)
        resource = await self._resource(await self._load(cohort_id, context), context)
        self._require(context, OrganizationAction.ASSIGNMENT_CREATE, resource)
        cohort_id = resource["cohort_id"]
        rows = await self.repository.snapshot_member_rows(
            context.organization_id, cohort_id, limit=limit,
            organization_memberships_collection=self.organization_memberships,
        )
        if len(rows) > limit:
            raise HTTPException(413, f"Cohort exceeds the {limit}-recipient assignment limit")
        users = await self._users_by_id([row["user_id"] for row in rows])
        recipients = []
        for row in rows:
            user = users.get(row["user_id"])
            if user is None:
                continue
            if not user.get("email"):
                raise HTTPException(409, "An active cohort member has no delivery email")
            recipients.append({
                "user_id": row["user_id"], "email": user["email"],
                "name": self._display_name(user), "cohort_id": cohort_id,
            })
        return recipients
