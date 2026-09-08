import inspect
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException, Response
from fastapi.params import Depends

from server.app.auth import routes as auth_routes
from server.app.auth.services import login_service
from server.app.users import routes as user_routes
from server.app.users.models import UpdatePersonaRequest, UserOut
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
        )

    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"
    assert result["is_verified"] is False
    users_collection.update_one.assert_awaited_once()


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
    ) as get_questions_mock:
        result = await get_quiz(
            MagicMock(), Response(), request, current_user=current_user
        )

    assert result == {"source": "mock", "questions": []}
    get_questions_mock.assert_awaited_once_with(
        request,
        user_id=current_user.id,
        invitation_repository=ANY,
        email_service=ANY,
    )


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
