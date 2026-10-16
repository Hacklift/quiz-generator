from unittest.mock import AsyncMock
from types import SimpleNamespace

import jwt
import pytest
from bson import ObjectId
from fastapi import HTTPException

from server.app.core.config import settings
from server.app.organizations.onboarding import accept_onboarding_token
from server.app.users.models import UserOut, UpdateLocaleRequest
from server.app.users.services import update_user_locale_service


USER_ID = "507f1f77bcf86cd799439011"
ORG_ID = "507f1f77bcf86cd799439012"


@pytest.mark.asyncio
async def test_unverified_independent_user_can_save_preference():
    user = UserOut(id=USER_ID, username="learner", email="learner@example.com", is_verified=False)
    users = SimpleNamespace(
        update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        find_one=AsyncMock(return_value={"_id": ObjectId(USER_ID), "username": user.username, "email": user.email,
                                       "profile": {"preferred_locale": "yo", "language_selected": True}}),
    )
    response = await update_user_locale_service(UpdateLocaleRequest(preferred_locale="yo"), user, users)
    assert response.user.preferred_locale == "yo"
    assert response.user.effective_locale == "yo"
    assert response.user.language_selected is True
    written = users.update_one.call_args.args[1]["$set"]
    assert written["profile.preferred_locale"] == "yo"
    assert "profile.active_organization_id" not in written


@pytest.mark.asyncio
async def test_email_bound_invitation_records_provenance_without_overwriting_preference():
    user = UserOut(id=USER_ID, username="learner", email="learner@example.com", preferred_locale="es")
    token = jwt.encode({"type": "organization_onboarding", "organization_id": ORG_ID,
                        "email": user.email, "exp": 4102444800}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    organizations = SimpleNamespace(find_one=AsyncMock(return_value={"_id": ObjectId(ORG_ID)}))
    memberships = SimpleNamespace(update_one=AsyncMock())
    users = SimpleNamespace(update_one=AsyncMock())
    await accept_onboarding_token(token, user, organizations, memberships, users)
    assert users.update_one.call_args.args[0]["profile.onboarding_organization_id"] is None
    written = users.update_one.call_args.args[1]["$set"]
    assert written["profile.onboarding_organization_id"] == ORG_ID
    assert "profile.preferred_locale" not in written
    wrong_user = user.model_copy(update={"email": "someone-else@example.com"})
    with pytest.raises(HTTPException):
        await accept_onboarding_token(token, wrong_user, organizations, memberships, users)
    assert users.update_one.await_count == 1
