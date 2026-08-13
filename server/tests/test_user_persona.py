from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from pydantic import ValidationError

from server.app.users.models import UpdatePersonaRequest, UpdateProfileRequest, UserPersona
from server.app.users.persona import (
    PERSONA_CATEGORIES,
    PERSONA_USER_TYPES,
    build_persona,
    category_for_user_type,
    get_persona,
    normalize_persona_category,
    normalize_persona_user_type,
    persona_pair_is_valid,
    persona_update_fields,
)
from server.app.users.repository import build_user_out_payload
from server.app.users.services import (
    update_user_persona_service,
    update_user_profile_service,
)


def _user_doc(**overrides):
    doc = {
        "_id": ObjectId(),
        "username": "persona-user",
        "email": "persona@example.com",
        "is_verified": True,
        "is_active": True,
        "status": "active",
    }
    doc.update(overrides)
    return doc


class TestNormalisation:
    def test_normalizes_case_and_whitespace(self):
        assert normalize_persona_category("  School ") == "school"
        assert normalize_persona_user_type("HR") == "hr"

    def test_rejects_unknown_values(self):
        assert normalize_persona_category("university") is None
        assert normalize_persona_user_type("principal") is None
        assert normalize_persona_user_type(None) is None

    def test_category_lookup(self):
        assert category_for_user_type("teacher") == "school"
        assert category_for_user_type("hr") == "corporate"
        assert category_for_user_type("nope") is None

    def test_every_user_type_belongs_to_a_category(self):
        for user_type in PERSONA_USER_TYPES:
            assert category_for_user_type(user_type) in PERSONA_CATEGORIES


class TestPairValidation:
    def test_accepts_matching_pair(self):
        assert persona_pair_is_valid("school", "teacher") is True
        assert persona_pair_is_valid("corporate", "hr") is True

    def test_accepts_both_unset(self):
        assert persona_pair_is_valid(None, None) is True

    def test_rejects_mismatched_pair(self):
        assert persona_pair_is_valid("corporate", "teacher") is False

    def test_rejects_half_set_pair(self):
        assert persona_pair_is_valid("school", None) is False
        assert persona_pair_is_valid(None, "teacher") is False


class TestBuildAndRead:
    def test_build_persona_defaults_to_unset(self):
        persona = build_persona()
        assert persona == {
            "category": None,
            "user_type": None,
            "set_at": None,
            "source": "unset",
        }

    def test_build_persona_infers_category(self):
        persona = build_persona(user_type="lecturer", source="onboarding")
        assert persona["category"] == "school"
        assert persona["source"] == "onboarding"

    def test_get_persona_on_legacy_doc_without_profile(self):
        assert get_persona(_user_doc())["user_type"] is None

    def test_get_persona_reads_nested_document(self):
        doc = _user_doc(
            profile={"persona": {"category": "corporate", "user_type": "employee"}}
        )
        assert get_persona(doc)["user_type"] == "employee"


class TestUserOutPayload:
    def test_legacy_user_without_persona_serialises_to_none(self):
        """Regression guard: pre-#119 users must keep working."""
        payload = build_user_out_payload(_user_doc(profile={"full_name": "Ada"}))

        assert payload["persona_category"] is None
        assert payload["persona_user_type"] is None
        assert payload["persona_set_at"] is None
        assert payload["full_name"] == "Ada"

    def test_persona_is_flattened_and_isoformatted(self):
        set_at = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
        doc = _user_doc(
            profile={
                "persona": {
                    "category": "school",
                    "user_type": "teacher",
                    "set_at": set_at,
                    "source": "onboarding",
                }
            }
        )

        payload = build_user_out_payload(doc)

        assert payload["persona_category"] == "school"
        assert payload["persona_user_type"] == "teacher"
        assert payload["persona_set_at"] == set_at.isoformat()


class TestUpdateProfileRequest:
    def test_accepts_valid_pair(self):
        request = UpdateProfileRequest(
            persona_category="school", persona_user_type="parent"
        )
        assert request.persona_user_type == "parent"

    def test_accepts_absent_persona(self):
        assert UpdateProfileRequest(full_name="Ada").persona_category is None

    def test_rejects_mismatched_pair(self):
        with pytest.raises(ValidationError):
            UpdateProfileRequest(
                persona_category="corporate", persona_user_type="teacher"
            )

    def test_rejects_half_set_pair(self):
        with pytest.raises(ValidationError):
            UpdateProfileRequest(persona_user_type="teacher")


class TestUpdatePersonaRequest:
    def test_accepts_valid_pair_and_source(self):
        request = UpdatePersonaRequest(
            persona_category="school",
            persona_user_type="teacher",
            source="onboarding",
        )

        assert request.persona_category == "school"
        assert request.persona_user_type == "teacher"
        assert request.source == "onboarding"

    def test_rejects_mismatched_pair(self):
        with pytest.raises(ValidationError):
            UpdatePersonaRequest(
                persona_category="corporate",
                persona_user_type="teacher",
            )

    def test_rejects_unknown_source(self):
        with pytest.raises(ValidationError):
            UpdatePersonaRequest(
                persona_category="school",
                persona_user_type="teacher",
                source="signup",
            )


class TestUserPersonaModel:
    def test_rejects_user_type_outside_category(self):
        with pytest.raises(ValidationError):
            UserPersona(category="school", user_type="hr")

    def test_allows_fully_unset(self):
        assert UserPersona().user_type is None


class TestPersonaUpdateFields:
    def test_returns_nothing_when_persona_absent(self):
        assert persona_update_fields(None, None) == {}

    def test_produces_dotted_paths(self):
        fields = persona_update_fields("school", "teacher")

        assert fields["profile.persona.category"] == "school"
        assert fields["profile.persona.user_type"] == "teacher"
        assert fields["profile.persona.source"] == "profile"
        assert isinstance(fields["profile.persona.set_at"], datetime)


class TestUpdateProfileService:
    @pytest.mark.asyncio
    async def test_persists_persona_via_dotted_paths(self):
        user_id = ObjectId()
        stored = _user_doc(_id=user_id)
        collection = AsyncMock()
        collection.update_one.return_value = AsyncMock(modified_count=1)
        collection.find_one.return_value = stored

        current_user = type(
            "CurrentUser", (), {"id": str(user_id)}
        )()

        await update_user_profile_service(
            UpdateProfileRequest(
                persona_category="corporate", persona_user_type="hr"
            ),
            current_user,
            collection,
        )

        update_doc = collection.update_one.await_args.args[1]["$set"]
        assert update_doc["profile.persona.category"] == "corporate"
        assert update_doc["profile.persona.user_type"] == "hr"
        assert "updated_at" in update_doc

    @pytest.mark.asyncio
    async def test_leaves_persona_untouched_when_not_supplied(self):
        user_id = ObjectId()
        collection = AsyncMock()
        collection.update_one.return_value = AsyncMock(modified_count=1)
        collection.find_one.return_value = _user_doc(_id=user_id)

        current_user = type("CurrentUser", (), {"id": str(user_id)})()

        await update_user_profile_service(
            UpdateProfileRequest(full_name="Ada"), current_user, collection
        )

        update_doc = collection.update_one.await_args.args[1]["$set"]
        assert not any(key.startswith("profile.persona") for key in update_doc)
        assert update_doc["profile.full_name"] == "Ada"


class TestUpdatePersonaService:
    @pytest.mark.asyncio
    async def test_persists_only_persona_fields_for_authenticated_user(self):
        user_id = ObjectId()
        stored = _user_doc(
            _id=user_id,
            profile={
                "persona": {
                    "category": "corporate",
                    "user_type": "employee",
                }
            },
        )
        collection = AsyncMock()
        collection.update_one.return_value = AsyncMock(modified_count=1)
        collection.find_one.return_value = stored

        current_user = type("CurrentUser", (), {"id": str(user_id)})()

        await update_user_persona_service(
            UpdatePersonaRequest(
                persona_category="corporate",
                persona_user_type="employee",
                source="inferred",
            ),
            current_user,
            collection,
        )

        update_doc = collection.update_one.await_args.args[1]["$set"]
        assert set(update_doc) == {
            "profile.persona.category",
            "profile.persona.user_type",
            "profile.persona.source",
            "profile.persona.set_at",
            "updated_at",
        }
        assert update_doc["profile.persona.category"] == "corporate"
        assert update_doc["profile.persona.user_type"] == "employee"
        assert update_doc["profile.persona.source"] == "inferred"
        assert isinstance(update_doc["profile.persona.set_at"], datetime)
