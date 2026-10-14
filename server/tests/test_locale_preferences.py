from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.app.i18n.locales import DEFAULT_LOCALE, resolve_effective_locale
from server.app.organizations.services import resolve_user_effective_locale
from server.app.quiz.utils.huggingface_utils import build_prompt
from server.app.users.models import UpdateLocaleRequest, UserOut


class FakeCollection:
    def __init__(self, document):
        self.document = document

    async def find_one(self, _query):
        return self.document


def make_user(**overrides) -> UserOut:
    payload = {
        "id": "507f1f77bcf86cd799439011",
        "username": "learner",
        "email": "learner@example.com",
        "is_verified": True,
    }
    payload.update(overrides)
    return UserOut(**payload)


def test_resolve_effective_locale_uses_platform_fallback_for_unknown_values():
    assert resolve_effective_locale("es") == "es"
    assert resolve_effective_locale("de") == "de"
    assert resolve_effective_locale("invalid") == DEFAULT_LOCALE
    assert resolve_effective_locale(None) == DEFAULT_LOCALE


def test_locale_update_accepts_supported_locale_or_inheritance_only():
    assert UpdateLocaleRequest(preferred_locale="fr").preferred_locale == "fr"
    assert UpdateLocaleRequest(preferred_locale=None).preferred_locale is None
    with pytest.raises(ValidationError):
        UpdateLocaleRequest(preferred_locale="invalid")
    assert UpdateLocaleRequest(preferred_locale="yo").preferred_locale == "yo"
    assert UpdateLocaleRequest(preferred_locale="ar").preferred_locale == "ar"


@pytest.mark.asyncio
async def test_user_preference_overrides_organization_default():
    user = make_user(preferred_locale="fr", active_organization_id="507f1f77bcf86cd799439012")
    locale = await resolve_user_effective_locale(
        user,
        FakeCollection({"default_locale": "es"}),
        FakeCollection({"role": "member"}),
    )
    assert locale == "fr"


@pytest.mark.asyncio
async def test_organization_default_is_used_when_user_inherits():
    user = make_user(onboarding_organization_id="507f1f77bcf86cd799439012")
    locale = await resolve_user_effective_locale(
        user,
        FakeCollection({"default_locale": "es"}),
        FakeCollection({"role": "member"}),
    )
    assert locale == "es"


@pytest.mark.asyncio
async def test_ordinary_membership_does_not_choose_language():
    user = make_user(active_organization_id="507f1f77bcf86cd799439012")
    assert await resolve_user_effective_locale(user, FakeCollection({"default_locale": "fr"}), FakeCollection({"role": "member"})) == "en"


@pytest.mark.asyncio
async def test_independent_user_can_choose_any_registered_language():
    user = make_user(preferred_locale="yo")
    assert await resolve_user_effective_locale(user, FakeCollection(None), FakeCollection(None)) == "yo"


@pytest.mark.asyncio
async def test_explicit_english_overrides_onboarding_organization():
    user = make_user(preferred_locale="en", onboarding_organization_id="507f1f77bcf86cd799439012")
    assert await resolve_user_effective_locale(user, FakeCollection({"default_locale": "fr"}), FakeCollection({"role": "member"})) == "en"


@pytest.mark.asyncio
async def test_departed_organization_does_not_supply_default():
    user = make_user(onboarding_organization_id="507f1f77bcf86cd799439012")
    assert await resolve_user_effective_locale(user, FakeCollection({"default_locale": "fr"}), FakeCollection(None)) == "en"


def test_standard_generation_prompt_requires_the_target_locale():
    prompt = build_prompt(
        "Photosynthesis",
        "multichoice",
        "medium",
        3,
        "students",
        None,
        "fr",
    )
    assert "locale `fr`" in prompt
    assert "question text, option text, answer text, and explanations" in prompt
