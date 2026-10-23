import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException, Response
from fastapi.params import Depends

from server.app.auth import routes as auth_routes
from server.app.auth import services as auth_services
from server.app.auth.services import login_service, register_user_service
from server.app.organizations.service import (
    OrganizationProvisioningConflictError,
    PersonalOrganizationMembershipInactiveError,
)
from server.app.users import routes as user_routes
from server.app.users.models import UpdatePersonaRequest, UserOut
from server.app.users.schemas import NewUserSchema, UserRegisterSchema
from server.app.core.dependencies import get_current_user, get_verified_user
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.routes.generation import get_quiz
from server.app.quiz.routes.downloads import download_quiz_handler, limiter
from server.app.quiz.schemas.download_query import DownloadQuizQuery


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    original_enabled = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original_enabled


def _user(is_verified: bool) -> UserOut:
    return UserOut(
        id=str(ObjectId()),
        username="progressive-user",
        email="progressive@example.com",
        is_verified=is_verified,
        is_active=True,
        role="user",
    )


def _assert_uses_verified_dependency(endpoint, parameter_name: str = "current_user"):
    dependency = inspect.signature(endpoint).parameters[parameter_name].default
    assert isinstance(dependency, Depends)
    assert dependency.dependency is get_verified_user


def _request_with_users_collection(users_collection):
    return type(
        "Request",
        (),
        {
            "app": type(
                "App",
                (),
                {"state": type("State", (), {"users_collection": users_collection})()},
            )()
        },
    )()


@pytest.mark.asyncio
async def test_unverified_user_can_login():
    user_id = ObjectId()
    users_collection = AsyncMock()
    sessions_collection = AsyncMock()
    auth_events_collection = AsyncMock()
    organization_provisioner = AsyncMock()
    organization_provisioner.ensure_personal_organization.return_value = {
        "_id": ObjectId()
    }
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "unverified",
        "email": "unverified@example.com",
        "hashed_password": "hashed",
        "is_verified": False,
        "status": "pending_verification",
    }

    with patch("server.app.auth.services.verify_password", return_value=True), patch(
        "server.app.auth.services.create_access_token",
        return_value="access-token",
    ), patch(
        "server.app.auth.services.create_refresh_token",
        return_value=("refresh-token", "refresh-jti", None),
    ), patch(
        "server.app.auth.services.hash_token",
        return_value="hashed-refresh-token",
    ):
        result = await login_service(
            identifier="unverified@example.com",
            password="password",
            users_collection=users_collection,
            sessions_collection=sessions_collection,
            auth_events_collection=auth_events_collection,
            organization_provisioner=organization_provisioner,
        )

    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"
    assert result["is_verified"] is False
    users_collection.update_one.assert_awaited_once()
    organization_provisioner.ensure_personal_organization.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_repairs_missing_personal_owner_membership():
    user_id = ObjectId()
    organization_id = str(ObjectId())
    users_collection = AsyncMock()
    sessions_collection = AsyncMock()
    auth_events_collection = AsyncMock()
    provisioner = AsyncMock()
    provisioner.ensure_personal_organization.return_value = {"_id": ObjectId(organization_id)}
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "member-repair",
        "email": "repair@example.com",
        "hashed_password": "hashed",
        "is_verified": True,
        "status": "active",
        "default_organization_id": organization_id,
    }

    with patch("server.app.auth.services.verify_password", return_value=True), patch(
        "server.app.auth.services.create_access_token", return_value="access-token"
    ), patch(
        "server.app.auth.services.create_refresh_token", return_value=("refresh-token", "jti", None)
    ), patch("server.app.auth.services.hash_token", return_value="hashed-token"), patch.object(
        auth_services.OrganizationRepository, "get_active", new=AsyncMock(return_value={
            "_id": ObjectId(organization_id), "kind": "personal", "personal_owner_user_id": str(user_id)
        })
    ), patch.object(
        auth_services.OrganizationMembershipRepository,
        "get_active_membership",
        new=AsyncMock(return_value=None),
    ):
        await login_service(
            identifier="repair@example.com",
            password="password",
            users_collection=users_collection,
            sessions_collection=sessions_collection,
            auth_events_collection=auth_events_collection,
            organization_provisioner=provisioner,
        )

    provisioner.ensure_personal_organization.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_falls_back_to_personal_tenant_when_default_membership_is_missing():
    user_id = ObjectId()
    former_organization_id = str(ObjectId())
    personal_organization_id = str(ObjectId())
    users_collection = AsyncMock()
    provisioner = AsyncMock()
    provisioner.ensure_personal_organization.return_value = {"_id": ObjectId(personal_organization_id)}
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "former-member",
        "email": "former-member@example.com",
        "hashed_password": "hashed",
        "is_verified": True,
        "status": "active",
        "default_organization_id": former_organization_id,
    }

    with patch("server.app.auth.services.verify_password", return_value=True), patch(
        "server.app.auth.services.create_access_token", return_value="access-token"
    ), patch(
        "server.app.auth.services.create_refresh_token", return_value=("refresh-token", "jti", None)
    ), patch("server.app.auth.services.hash_token", return_value="hashed-token"), patch(
        "server.app.auth.services.create_user_session", new=AsyncMock()
    ) as create_session, patch(
        "server.app.auth.services.record_auth_event", new=AsyncMock()
    ) as record_event, patch.object(
        auth_services.OrganizationRepository,
        "get_active",
        new=AsyncMock(return_value={"_id": ObjectId(former_organization_id), "kind": "corporate"}),
    ), patch.object(
        auth_services.OrganizationMembershipRepository,
        "get_active_membership",
        new=AsyncMock(return_value=None),
    ):
        await login_service(
            identifier="former-member@example.com",
            password="password",
            users_collection=users_collection,
            sessions_collection=AsyncMock(),
            auth_events_collection=AsyncMock(),
            organization_provisioner=provisioner,
        )

    provisioner.ensure_personal_organization.assert_awaited_once_with(
        user_id=str(user_id),
        organization_name="former-member",
        replace_conflicting_default=True,
    )
    assert create_session.await_args.kwargs["active_organization_id"] == personal_organization_id
    assert any(
        call.kwargs.get("event_type") == "organization_default_recovered"
        for call in record_event.await_args_list
    )


@pytest.mark.asyncio
async def test_login_uses_another_active_membership_when_personal_membership_is_suspended():
    user_id = ObjectId()
    inaccessible_default_id = str(ObjectId())
    fallback_organization_id = str(ObjectId())
    users_collection = AsyncMock()
    provisioner = AsyncMock()
    provisioner.ensure_personal_organization.side_effect = PersonalOrganizationMembershipInactiveError(
        "personal membership is suspended"
    )
    provisioner.find_active_organization_for_user.return_value = {
        "_id": ObjectId(fallback_organization_id)
    }
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "shared-member",
        "email": "shared-member@example.com",
        "hashed_password": "hashed",
        "is_verified": True,
        "status": "active",
        "default_organization_id": inaccessible_default_id,
    }

    with patch("server.app.auth.services.verify_password", return_value=True), patch(
        "server.app.auth.services.create_access_token", return_value="access-token"
    ), patch(
        "server.app.auth.services.create_refresh_token", return_value=("refresh-token", "jti", None)
    ), patch("server.app.auth.services.hash_token", return_value="hashed-token"), patch(
        "server.app.auth.services.create_user_session", new=AsyncMock()
    ) as create_session, patch(
        "server.app.auth.services.record_auth_event", new=AsyncMock()
    ) as record_event, patch.object(
        auth_services.OrganizationRepository,
        "get_active",
        new=AsyncMock(return_value=None),
    ), patch.object(
        auth_services.OrganizationMembershipRepository,
        "get_active_membership",
        new=AsyncMock(return_value=None),
    ):
        await login_service(
            identifier="shared-member@example.com",
            password="password",
            users_collection=users_collection,
            sessions_collection=AsyncMock(),
            auth_events_collection=AsyncMock(),
            organization_provisioner=provisioner,
        )

    provisioner.set_default_organization.assert_awaited_once_with(
        user_id=str(user_id),
        organization_id=fallback_organization_id,
        expected_default_organization_id=inaccessible_default_id,
    )
    assert create_session.await_args.kwargs["active_organization_id"] == fallback_organization_id
    assert any(
        call.kwargs.get("event_type") == "organization_default_recovered"
        for call in record_event.await_args_list
    )


@pytest.mark.asyncio
async def test_login_returns_conflict_when_fallback_default_changes_concurrently():
    user_id = ObjectId()
    inaccessible_default_id = str(ObjectId())
    users_collection = AsyncMock()
    provisioner = AsyncMock()
    provisioner.ensure_personal_organization.side_effect = PersonalOrganizationMembershipInactiveError(
        "personal membership is suspended"
    )
    provisioner.find_active_organization_for_user.return_value = {"_id": ObjectId()}
    provisioner.set_default_organization.side_effect = OrganizationProvisioningConflictError(
        "default changed"
    )
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "shared-member",
        "email": "shared-member@example.com",
        "hashed_password": "hashed",
        "is_verified": True,
        "status": "active",
        "default_organization_id": inaccessible_default_id,
    }

    with patch("server.app.auth.services.verify_password", return_value=True), patch.object(
        auth_services.OrganizationRepository,
        "get_active",
        new=AsyncMock(return_value=None),
    ), patch.object(
        auth_services.OrganizationMembershipRepository,
        "get_active_membership",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc:
            await login_service(
                identifier="shared-member@example.com",
                password="password",
                users_collection=users_collection,
                sessions_collection=AsyncMock(),
                auth_events_collection=AsyncMock(),
                organization_provisioner=provisioner,
            )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("provisioning_deferred", [False, True])
async def test_registration_preserves_verification_and_analytics_with_tenant_provisioning(
    provisioning_deferred,
):
    timestamp = datetime.now(timezone.utc)
    created_user = NewUserSchema(
        id=str(ObjectId()),
        username="new-user",
        email="new-user@example.com",
        full_name="New User",
        is_active=True,
        is_verified=False,
        status="pending_verification",
        role="user",
        created_at=timestamp,
        updated_at=timestamp,
    )
    users_collection = AsyncMock()
    users_collection.find_one.return_value = None
    redis_client = AsyncMock()
    email_service = AsyncMock()
    auth_events_collection = AsyncMock()

    with patch.object(auth_services, "users_collection", users_collection), patch(
        "server.app.auth.services.create_user", new=AsyncMock(return_value=created_user)
    ), patch(
        "server.app.auth.services.get_auth_events_collection", return_value=auth_events_collection
    ), patch(
        "server.app.auth.services.get_organizations_collection", return_value=AsyncMock()
    ), patch(
        "server.app.auth.services.get_organization_memberships_collection", return_value=AsyncMock()
    ), patch.object(
        auth_services.OrganizationProvisioningService,
        "ensure_personal_organization",
        new=AsyncMock(
            side_effect=RuntimeError("tenant store unavailable") if provisioning_deferred else None
        ),
    ), patch(
        "server.app.auth.services.record_auth_event", wraps=auth_services.record_auth_event
    ) as record_event, patch(
        "server.app.auth.services.get_redis_client", new=AsyncMock(return_value=redis_client)
    ), patch("server.app.auth.services.generate_otp", return_value="123456"), patch(
        "server.app.auth.services.generate_verification_token", return_value="verification-token"
    ):
        result = await register_user_service(
            UserRegisterSchema(
                username="new-user",
                email="new-user@example.com",
                full_name="New User",
                password="Password1!",
            ),
            email_service,
        )

    assert result.id == created_user.id
    assert redis_client.setex.await_count == 2
    email_service.send_email.assert_awaited_once()
    assert record_event.await_args.kwargs["user"] is created_user
    auth_events_collection.insert_one.assert_awaited_once()
    event = auth_events_collection.insert_one.await_args.args[0]
    assert event["event_type"] == "register"
    assert event["user_id"] == created_user.id
    assert event["metadata"] == {
        "tenant_provisioning_pending": provisioning_deferred,
        "persona": {"category": "unset", "user_type": "unset"},
    }


@pytest.mark.asyncio
async def test_login_returns_conflict_for_unrecoverable_tenant_default():
    user_id = ObjectId()
    users_collection = AsyncMock()
    provisioner = AsyncMock()
    provisioner.ensure_personal_organization.side_effect = OrganizationProvisioningConflictError("conflict")
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "conflict-user",
        "email": "conflict@example.com",
        "hashed_password": "hashed",
        "is_verified": True,
        "status": "active",
        "default_organization_id": "",
    }

    with patch("server.app.auth.services.verify_password", return_value=True):
        with pytest.raises(HTTPException) as exc:
            await login_service(
                identifier="conflict@example.com",
                password="password",
                users_collection=users_collection,
                sessions_collection=AsyncMock(),
                auth_events_collection=AsyncMock(),
                organization_provisioner=provisioner,
            )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_unverified_user_can_generate_quiz():
    request = QuizRequest(
        profession="teacher",
        num_questions=1,
        question_type="multichoice",
        difficulty_level="easy",
        audience_type="students",
        token=None,
    )
    current_user = _user(is_verified=False)

    with patch(
        "server.app.quiz.routes.generation.get_questions",
        new=AsyncMock(return_value={"source": "mock", "questions": []}),
    ) as get_questions_mock, patch(
        "server.app.quiz.routes.generation.record_product_event_safely",
        new=AsyncMock(),
    ) as record_event_mock, patch(
        "server.app.quiz.routes.generation.get_product_events_collection",
        return_value=MagicMock(),
    ):
        result = await get_quiz(MagicMock(), Response(), request, current_user=current_user)

    assert result == {"source": "mock", "questions": []}
    get_questions_mock.assert_awaited_once_with(
        request,
        user_id=current_user.id,
        invitation_repository=ANY,
        email_service=ANY,
    )
    record_event_mock.assert_awaited_once()
    assert record_event_mock.await_args.kwargs["event_type"] == "quiz_generated"
    assert record_event_mock.await_args.kwargs["user"] is current_user
    assert record_event_mock.await_args.kwargs["origin"] == "rest"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("access_code_created", "expected_event_count"),
    [(True, 2), (False, 1)],
)
async def test_standard_generation_records_live_event_only_for_new_activation(
    access_code_created, expected_event_count
):
    request = QuizRequest(
        profession="teacher",
        num_questions=1,
        question_type="multichoice",
        difficulty_level="easy",
        audience_type="students",
        token=None,
    )
    current_user = _user(is_verified=True)
    generated = {
        "source": "mock",
        "questions": [],
        "quiz_id": "quiz-1",
        "live_quiz_enabled": True,
        "_access_code_created": access_code_created,
    }

    with patch(
        "server.app.quiz.routes.generation.get_questions",
        new=AsyncMock(return_value=generated),
    ), patch(
        "server.app.quiz.routes.generation.record_product_event_safely",
        new=AsyncMock(),
    ) as record_event_mock:
        result = await get_quiz(
            MagicMock(), Response(), request, current_user=current_user
        )

    assert "_access_code_created" not in result
    assert record_event_mock.await_count == expected_event_count
    event_types = [
        call.kwargs["event_type"] for call in record_event_mock.await_args_list
    ]
    assert event_types.count("quiz_generated") == 1
    assert event_types.count("live_quiz_enabled") == int(access_code_created)


@pytest.mark.asyncio
async def test_quiz_generation_response_is_not_delayed_by_slow_telemetry(monkeypatch):
    async def slow_insert(_event):
        await asyncio.sleep(1)

    request = QuizRequest(
        profession="teacher",
        num_questions=1,
        question_type="multichoice",
        difficulty_level="easy",
        audience_type="students",
        token=None,
    )
    monkeypatch.setattr(
        "server.app.analytics.product_events.settings.PRODUCT_EVENT_TIMEOUT_SECONDS",
        0.01,
    )
    monkeypatch.setattr(
        "server.app.quiz.routes.generation.get_questions",
        AsyncMock(return_value={"source": "mock", "questions": []}),
    )
    monkeypatch.setattr(
        "server.app.quiz.routes.generation.get_product_events_collection",
        lambda: SimpleNamespace(insert_one=slow_insert),
    )
    loop = asyncio.get_running_loop()
    started_at = loop.time()

    result = await get_quiz(
        MagicMock(),
        Response(),
        request,
        current_user=_user(is_verified=True),
    )

    assert result == {"source": "mock", "questions": []}
    assert loop.time() - started_at < 0.2


@pytest.mark.asyncio
async def test_unverified_user_cannot_use_verified_dependency():
    with pytest.raises(HTTPException) as exc:
        await get_verified_user(current_user=_user(is_verified=False))

    assert exc.value.status_code == 403
    assert exc.value.detail == "Email not verified"


@pytest.mark.asyncio
async def test_verified_user_can_use_verified_dependency():
    current_user = _user(is_verified=True)

    assert await get_verified_user(current_user=current_user) is current_user


def test_sensitive_auth_routes_require_verified_user():
    _assert_uses_verified_dependency(user_routes.update_profile)
    _assert_uses_verified_dependency(user_routes.request_email_change)
    _assert_uses_verified_dependency(user_routes.verify_email_change)


def test_persona_update_requires_authentication_but_not_verification():
    dependency = inspect.signature(user_routes.update_persona).parameters[
        "current_user"
    ].default
    assert isinstance(dependency, Depends)
    assert dependency.dependency is get_current_user


@pytest.mark.asyncio
async def test_persona_update_route_allows_unverified_authenticated_user():
    user_id = ObjectId()
    users_collection = AsyncMock()
    users_collection.update_one.return_value = AsyncMock(modified_count=1)
    users_collection.find_one.return_value = {
        "_id": user_id,
        "username": "unverified",
        "email": "unverified@example.com",
        "is_verified": False,
        "is_active": True,
        "status": "pending_verification",
        "profile": {
            "persona": {
                "category": "school",
                "user_type": "teacher",
                "source": "onboarding",
            }
        },
    }

    result = await user_routes.update_persona(
        _request_with_users_collection(users_collection),
        Response(),
        UpdatePersonaRequest(
            persona_category="school",
            persona_user_type="teacher",
            source="onboarding",
        ),
        current_user=UserOut(
            id=str(user_id),
            username="unverified",
            email="unverified@example.com",
            is_verified=False,
            is_active=True,
            status="pending_verification",
        ),
    )

    assert result.message == "Persona updated successfully"
    assert result.user.persona_category == "school"
    assert result.user.persona_user_type == "teacher"
    users_collection.update_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_persona_update_route_returns_400_for_invalid_current_user_id():
    users_collection = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await user_routes.update_persona(
            _request_with_users_collection(users_collection),
            Response(),
            UpdatePersonaRequest(
                persona_category="school",
                persona_user_type="teacher",
            ),
            current_user=UserOut(
                id="not-an-object-id",
                username="user",
                email="user@example.com",
            ),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_persona_update_route_returns_404_for_deleted_or_missing_user():
    user_id = ObjectId()
    users_collection = AsyncMock()
    users_collection.update_one.return_value = AsyncMock(modified_count=0)
    users_collection.find_one.return_value = None

    with pytest.raises(HTTPException) as exc:
        await user_routes.update_persona(
            _request_with_users_collection(users_collection),
            Response(),
            UpdatePersonaRequest(
                persona_category="school",
                persona_user_type="teacher",
            ),
            current_user=UserOut(
                id=str(user_id),
                username="user",
                email="user@example.com",
            ),
        )

    assert exc.value.status_code == 404


def test_login_password_reset_and_verification_routes_do_not_require_verified_user():
    for endpoint in (
        auth_routes.login,
        auth_routes.request_password_reset,
        auth_routes.reset_password,
        auth_routes.verify_otp,
        auth_routes.verify_link,
        auth_routes.resend_verification,
    ):
        for parameter in inspect.signature(endpoint).parameters.values():
            default = parameter.default
            assert not (
                isinstance(default, Depends)
                and default.dependency is get_verified_user
            )


@pytest.mark.asyncio
async def test_authenticated_quiz_download_requires_authentication_for_quiz_id():
    with pytest.raises(HTTPException) as exc:
        await download_quiz_handler(
            request=MagicMock(),
            response=Response(),
            query=DownloadQuizQuery(
                quiz_id=str(ObjectId()),
                format="txt",
                question_type="multichoice",
                num_question=1,
            ),
            current_user=None,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Authentication required"


@pytest.mark.asyncio
async def test_unverified_user_cannot_download_authenticated_quiz():
    with pytest.raises(HTTPException) as exc:
        await download_quiz_handler(
            request=MagicMock(),
            response=Response(),
            query=DownloadQuizQuery(
                quiz_id=str(ObjectId()),
                format="txt",
                question_type="multichoice",
                num_question=1,
            ),
            current_user=_user(is_verified=False),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Email not verified"


@pytest.mark.asyncio
async def test_verified_user_can_download_authenticated_quiz():
    quiz_id = str(ObjectId())
    current_user = _user(is_verified=True)

    with patch(
        "server.app.quiz.routes.downloads.download_quiz_by_id",
        new=AsyncMock(return_value="streaming-response"),
    ) as download_mock:
        result = await download_quiz_handler(
            request=MagicMock(),
            response=Response(),
            query=DownloadQuizQuery(
                quiz_id=quiz_id,
                format="txt",
                question_type="multichoice",
                num_question=1,
            ),
            current_user=current_user,
        )

    assert result == "streaming-response"
    download_mock.assert_awaited_once_with(
        quiz_id=quiz_id,
        file_format="txt",
        user_id=current_user.id,
    )
