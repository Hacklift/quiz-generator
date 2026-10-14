from __future__ import annotations

from types import SimpleNamespace

import pytest

from server.app.mcp.context import McpRequestContext
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal


@pytest.mark.asyncio
async def test_mcp_share_link_rejects_a_private_quiz(monkeypatch):
    from server.app.mcp.tools import share_tools

    principal = OrganizationPrincipal(user_id="author-1", session_id="session-1")
    organization = OrganizationContext(
        organization_id="organization-1",
        organization_kind="corporate",
        membership_role="author",
        principal=principal,
        membership={"role": "author", "status": "active"},
    )
    context = McpRequestContext(
        user_id=principal.user_id,
        is_authenticated=True,
        organization_context=organization,
    )
    quiz = SimpleNamespace(
        model_dump=lambda **_kwargs: {
            "organization_id": organization.organization_id,
            "created_by_user_id": principal.user_id,
        }
    )

    class QuizRepository:
        def __init__(self, _collection):
            pass

        async def find_by_id_for_organization(self, quiz_id: str, organization_id: str):
            assert quiz_id == "private-quiz"
            assert organization_id == organization.organization_id
            return quiz

    class SharedQuizService:
        async def resolve_shared_quiz(self, quiz_id: str):
            assert quiz_id == "private-quiz"
            return None

    async def authenticated_context(**_kwargs):
        return context

    monkeypatch.setattr(share_tools, "get_mcp_request_context", authenticated_context)
    monkeypatch.setattr(share_tools, "get_quizzes_v2_collection", lambda: object())
    monkeypatch.setattr(share_tools, "QuizV2Repository", QuizRepository)
    monkeypatch.setattr(share_tools, "SharedQuizReadService", SharedQuizService)

    with pytest.raises(ValueError, match="public or unlisted"):
        await share_tools.share_create_link("private-quiz")
