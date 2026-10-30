from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Response
from fastapi.params import Depends
from unittest.mock import MagicMock
from pymongo.errors import ConnectionFailure, OperationFailure

from server.app.core.dependencies import get_verified_user
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


def _share_link_handler(routes):
    return getattr(routes.get_share_link, "__wrapped__", routes.get_share_link)


def test_email_sharing_requires_a_verified_user():
    from server.app.share import routes

    handler = getattr(routes.share_quiz_via_email, "__wrapped__", routes.share_quiz_via_email)
    dependency = inspect.signature(handler).parameters["current_user"].default
    assert isinstance(dependency, Depends)
    assert dependency.dependency is get_verified_user


@pytest.mark.asyncio
async def test_random_seed_quiz_requires_an_active_platform_library():
    from server.app.share import routes

    quizzes = MagicMock()
    quizzes.aggregate.return_value = SimpleNamespace(to_list=AsyncMock())
    organizations = MagicMock()
    organizations.find_one = AsyncMock(return_value=None)
    handler = getattr(routes.get_random_quiz_id, "__wrapped__", routes.get_random_quiz_id)

    with pytest.raises(HTTPException) as exc_info:
        await handler(
            request=MagicMock(),
            response=Response(),
            quizzes_v2_collection=quizzes,
            organizations_collection=organizations,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Public quiz library is unavailable"
    quizzes.aggregate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_stage", ["library", "sampling"])
async def test_random_seed_quiz_database_failure_returns_503(failure_stage, caplog):
    from server.app.share import routes

    quizzes = MagicMock()
    organizations = MagicMock()
    organizations.find_one = AsyncMock(return_value={"_id": "platform-library"})
    quizzes.aggregate.return_value = SimpleNamespace(to_list=AsyncMock())
    failure = ConnectionFailure("sensitive database diagnostics")
    if failure_stage == "library":
        organizations.find_one.side_effect = failure
    else:
        quizzes.aggregate.return_value.to_list.side_effect = failure
    handler = getattr(routes.get_random_quiz_id, "__wrapped__", routes.get_random_quiz_id)
    with pytest.raises(HTTPException) as exc:
        await handler(request=MagicMock(), response=Response(), quizzes_v2_collection=quizzes, organizations_collection=organizations)
    assert exc.value.status_code == 503
    assert exc.value.detail == "Public quiz library is temporarily unavailable"
    assert "Database unavailable while selecting a public template quiz" in caplog.text


@pytest.mark.asyncio
async def test_random_seed_query_error_is_not_misreported_as_empty_or_retryable():
    from server.app.share import routes

    quizzes = MagicMock()
    organizations = SimpleNamespace(find_one=AsyncMock(side_effect=OperationFailure("invalid query")))
    handler = getattr(routes.get_random_quiz_id, "__wrapped__", routes.get_random_quiz_id)
    with pytest.raises(HTTPException) as exc:
        await handler(request=MagicMock(), response=Response(), quizzes_v2_collection=quizzes, organizations_collection=organizations)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to fetch a public template quiz"
    quizzes.aggregate.assert_not_called()


@pytest.mark.asyncio
async def test_guest_can_create_a_link_only_for_an_anonymously_shareable_quiz(monkeypatch):
    from server.app.share import routes

    async def public_quiz(quiz_id: str):
        assert quiz_id == "public-quiz"
        return {"id": quiz_id}

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", public_quiz)

    response = await _share_link_handler(routes)(
        request=MagicMock(),
        response=Response(),
        quiz_id="public-quiz",
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
    monkeypatch.setattr(routes, "resolve_current_user_organization_context", stale_context)

    response = await _share_link_handler(routes)(
        request=MagicMock(),
        response=Response(),
        quiz_id="public-quiz",
        current_user=object(),
    )

    assert response["link"].endswith("/share/public-quiz")


@pytest.mark.asyncio
async def test_guest_cannot_create_a_link_for_a_private_quiz(monkeypatch):
    from server.app.share import routes

    async def private_quiz(_: str):
        return None

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", private_quiz)

    with pytest.raises(HTTPException) as exc_info:
        await _share_link_handler(routes)(
            request=MagicMock(),
            response=Response(),
            quiz_id="private-quiz",
            current_user=None,
        )

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
    monkeypatch.setattr(routes, "resolve_current_user_organization_context", active_context)

    with pytest.raises(HTTPException) as exc_info:
        await _share_link_handler(routes)(
            request=MagicMock(),
            response=Response(),
            quiz_id="tenant-quiz",
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
    monkeypatch.setattr(routes, "resolve_current_user_organization_context", active_context)

    with pytest.raises(HTTPException) as exc_info:
        await _share_link_handler(routes)(
            request=MagicMock(),
            response=Response(),
            quiz_id="private-quiz",
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


@pytest.mark.asyncio
async def test_email_sharing_requires_content_share_permission_even_for_public_quiz(monkeypatch):
    from server.app.share import routes
    from server.app.share.schemas import ShareEmailRequest

    async def public_quiz(_: str):
        return {"id": "public-quiz", "title": "Public quiz", "description": None}

    async def deny(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="Organization permission denied")

    monkeypatch.setattr(routes.shared_quiz_read_service, "resolve_shared_quiz", public_quiz)
    monkeypatch.setattr(routes, "_require_share_permission", deny)
    handler = getattr(routes.share_quiz_via_email, "__wrapped__", routes.share_quiz_via_email)

    with pytest.raises(HTTPException) as exc_info:
        await handler(
            request=None,
            response=None,
            query=ShareEmailRequest(
                quiz_id="public-quiz",
                recipient_email="recipient@example.com",
            ),
            email_svc=object(),
            current_user=object(),
            organization=_context(),
        )

    assert exc_info.value.status_code == 403
