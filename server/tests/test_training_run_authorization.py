import inspect

import pytest
from bson import ObjectId
from fastapi import HTTPException, Response
from fastapi.params import Depends

from server.app.core.dependencies import get_training_manager_user, get_verified_user
from server.app.quiz.routes import training_runs
from server.app.users.models import UserOut


def _user(*, category: str | None, user_type: str | None) -> UserOut:
    return UserOut(
        id=str(ObjectId()),
        username="training-user",
        email="training-user@example.com",
        is_verified=True,
        is_active=True,
        persona_category=category,
        persona_user_type=user_type,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("user_type", ["business", "hr"])
async def test_corporate_training_manager_personas_are_allowed(user_type: str):
    current_user = _user(category="corporate", user_type=user_type)

    assert await get_training_manager_user(current_user=current_user) is current_user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("category", "user_type"),
    [
        ("corporate", "employee"),
        ("school", "teacher"),
        (None, None),
    ],
)
async def test_non_manager_personas_are_denied_training_management(
    category: str | None, user_type: str | None
):
    with pytest.raises(HTTPException) as exc:
        await get_training_manager_user(
            current_user=_user(category=category, user_type=user_type)
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == (
        "Training run management is available to Business and HR personas"
    )


def test_training_management_routes_require_manager_capability():
    for endpoint in (
        training_runs.list_owned_training_quizzes,
        training_runs.create_training_run,
        training_runs.list_training_runs,
        training_runs.get_training_run,
        training_runs.close_training_run,
    ):
        dependency = inspect.signature(endpoint).parameters["current_user"].default
        assert isinstance(dependency, Depends)
        assert dependency.dependency is get_training_manager_user


def test_training_manager_capability_composes_verified_user_requirement():
    dependency = inspect.signature(get_training_manager_user).parameters[
        "current_user"
    ].default

    assert isinstance(dependency, Depends)
    assert dependency.dependency is get_verified_user


def test_rate_limited_training_routes_accept_fastapi_response():
    """SlowAPI requires Response to attach rate-limit headers after a success."""
    for endpoint in (
        training_runs.create_training_run,
        training_runs.preview_public_training_run,
        training_runs.start_public_training_run,
    ):
        response_parameter = inspect.signature(endpoint).parameters.get("response")
        assert response_parameter is not None
        assert response_parameter.annotation is Response
