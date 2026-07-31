"""Keeps the Python and TypeScript persona taxonomies in lockstep.

The client owns persona copy; this module owns the slugs. If the two ever
disagree, a persona set in the UI could be rejected by the API (or worse,
silently stored and never rendered), so drift fails the build here.

Skipped when client/ is absent — the server Docker image does not ship it.
"""
import re
from pathlib import Path
from typing import get_args

import pytest

from server.app.users.models import PersonaCategoryField, PersonaUserTypeField
from server.app.users.persona import (
    PERSONA_CATEGORIES,
    PERSONA_USER_TYPES,
    PERSONA_USER_TYPES_BY_CATEGORY,
)


PERSONA_TS = (
    Path(__file__).resolve().parents[2]
    / "client"
    / "src"
    / "shared"
    / "config"
    / "persona.ts"
)

requires_client = pytest.mark.skipif(
    not PERSONA_TS.exists(), reason="client/ not present in this build context"
)


def _const_array(source: str, name: str) -> set[str]:
    match = re.search(rf"export const {name} = \[(.*?)\] as const;", source, re.S)
    assert match, f"{name} not found in persona.ts"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


class TestPythonInternalConsistency:
    def test_flat_tuple_matches_category_map(self):
        expected = {t for types in PERSONA_USER_TYPES_BY_CATEGORY.values() for t in types}
        assert set(PERSONA_USER_TYPES) == expected

    def test_literal_annotations_match_tuples(self):
        # Literal cannot be built from a runtime tuple, so the annotation in
        # models.py is hand-written and needs pinning.
        assert set(get_args(PersonaCategoryField)) == set(PERSONA_CATEGORIES)
        assert set(get_args(PersonaUserTypeField)) == set(PERSONA_USER_TYPES)


@requires_client
class TestCrossLanguageParity:
    @pytest.fixture(scope="class")
    def source(self) -> str:
        return PERSONA_TS.read_text(encoding="utf-8")

    def test_categories_match(self, source):
        assert _const_array(source, "PERSONA_CATEGORIES") == set(PERSONA_CATEGORIES)

    def test_school_user_types_match(self, source):
        assert _const_array(source, "SCHOOL_USER_TYPES") == set(
            PERSONA_USER_TYPES_BY_CATEGORY["school"]
        )

    def test_corporate_user_types_match(self, source):
        assert _const_array(source, "CORPORATE_USER_TYPES") == set(
            PERSONA_USER_TYPES_BY_CATEGORY["corporate"]
        )
