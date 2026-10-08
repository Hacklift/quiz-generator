from __future__ import annotations

import pytest
from fastapi import HTTPException

from server.app.organizations.models import OrganizationContext, OrganizationPrincipal


def _context() -> OrganizationContext:
    principal = OrganizationPrincipal(user_id="author-1", session_id="session-1")
    return OrganizationContext(
        organization_id="organization-1",
        organization_kind="personal",
        membership_role="author",
        principal=principal,
        membership={"role": "author", "status": "active"},
    )


@pytest.mark.asyncio
async def test_guest_can_create_a_link_only_for_an_anonymously_shareable_quiz(monkeypatch):
    from server.app.share import routes

    async def public_quiz(quiz_id: str):
        assert quiz_id == "public-quiz"
        return {"id": quiz_id}

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", public_quiz)

    response = await routes.get_share_link(
        "public-quiz",
        current_user=None,
    )

    assert response["link"].endswith("/share/public-quiz")


@pytest.mark.asyncio
async def test_public_link_does_not_depend_on_a_stale_authenticated_tenant(monkeypatch):
    from server.app.share import routes

    async def public_quiz(_: str):
        return {"id": "public-quiz"}

    async def stale_context(*_args, **_kwargs):
        raise AssertionError("public link creation must not resolve tenant state")

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", public_quiz)
    monkeypatch.setattr(routes, "_resolve_share_organization", stale_context)

    response = await routes.get_share_link("public-quiz", current_user=object())

    assert response["link"].endswith("/share/public-quiz")


@pytest.mark.asyncio
async def test_guest_cannot_create_a_link_for_a_private_quiz(monkeypatch):
    from server.app.share import routes

    async def private_quiz(_: str):
        return None

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", private_quiz)

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_share_link("private-quiz", current_user=None)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [403, 404])
async def test_share_link_preserves_tenant_authorization_errors(monkeypatch, status_code: int):
    from server.app.share import routes

    async def private_quiz(_: str):
        return None

    async def deny(*_args, **_kwargs):
        raise HTTPException(status_code=status_code, detail="denied")

    async def active_context(*_args, **_kwargs):
        return _context()

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", private_quiz)
    monkeypatch.setattr(routes, "_require_share_permission", deny)
    monkeypatch.setattr(routes, "_resolve_share_organization", active_context)

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_share_link(
            "tenant-quiz",
            current_user=object(),
        )

    assert exc_info.value.status_code == status_code


@pytest.mark.asyncio
async def test_authorized_private_quiz_returns_a_clear_shareability_error(monkeypatch):
    from server.app.share import routes

    async def private_quiz(_: str):
        return None

    async def permit(*_args, **_kwargs):
        return object()

    async def active_context(*_args, **_kwargs):
        return _context()

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", private_quiz)
    monkeypatch.setattr(routes, "_require_share_permission", permit)
    monkeypatch.setattr(routes, "_resolve_share_organization", active_context)

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_share_link(
            "private-quiz",
            current_user=object(),
        )

    assert exc_info.value.status_code == 409
    assert "public or unlisted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authorized_private_quiz_cannot_be_shared_by_email(monkeypatch):
    from server.app.share import routes
    from server.app.share.schemas import ShareEmailRequest

    async def private_quiz(_: str):
        return None

    async def permit(*_args, **_kwargs):
        return object()

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", private_quiz)
    monkeypatch.setattr(routes, "_require_share_permission", permit)
    handler = getattr(routes.share_quiz_via_email, "__wrapped__", routes.share_quiz_via_email)

    with pytest.raises(HTTPException) as exc_info:
        await handler(
            request=None,
            response=None,
            query=ShareEmailRequest(
                quiz_id="private-quiz",
                recipient_email="recipient@example.com",
            ),
            email_svc=object(),
            current_user=object(),
            organization=_context(),
        )

    assert exc_info.value.status_code == 409
    assert "public or unlisted" in exc_info.value.detail
