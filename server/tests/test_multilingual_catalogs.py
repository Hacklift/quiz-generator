import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from server.app.i18n.catalogs import get_catalog, load_catalog, prepare_catalog_batch, source_version, validate_messages
from server.app.i18n.locales import SUPPORTED_LOCALES
from server.app.i18n.provider import TranslationProviderError


class Memory:
    def __init__(self, records=()):
        self.records = list(records)
        self.query = {}
        self.bulk_write = AsyncMock()

    def find(self, query):
        self.query = query
        return self

    async def to_list(self, length):
        return [r for r in self.records if all(
            r.get(key) in value["$in"] if isinstance(value, dict) else r.get(key) == value
            for key, value in self.query.items()
        )]


def flatten(data, prefix=""):
    result = {}
    for key, value in data.items():
        key = f"{prefix}.{key}" if prefix else key
        result.update({key: value} if isinstance(value, str) else flatten(value, key))
    return result


@pytest.mark.parametrize("namespace,prefix", [("translation", ""), ("persona", "persona."), ("ui", "ui.")])
@pytest.mark.parametrize("locale", ["en", "es", "fr"])
def test_bundled_catalogs_match_frontend_and_preserve_placeholders(namespace, prefix, locale):
    root = Path(__file__).resolve().parents[2]
    source = load_catalog("en", namespace)
    translated = load_catalog(locale, namespace)
    assert source and translated
    validate_messages(source, translated)
    frontend = json.loads((root / f"client/src/features/locale/messages/{prefix}{locale}.json").read_text())
    assert translated == flatten(frontend), "Regenerate server catalogs after editing UI messages"


def test_language_registry_is_shared_and_not_limited_to_fallbacks():
    root = Path(__file__).resolve().parents[2]
    client = json.loads((root / "client/src/features/locale/languages.json").read_text())
    assert {entry["code"] for entry in client} == SUPPORTED_LOCALES
    assert {"en", "es", "fr", "yo", "ar", "ja", "de", "ig"} <= SUPPORTED_LOCALES
    assert len(SUPPORTED_LOCALES) > 7000


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["es", "fr"])
async def test_fallback_never_requires_a_provider(locale, monkeypatch):
    provider = AsyncMock(side_effect=AssertionError("Fallback must work without LLM"))
    monkeypatch.setattr("server.app.i18n.catalogs.translate_messages", provider)
    source = load_catalog("en", "ui")
    catalog = await prepare_catalog_batch(Memory(), locale, "ui", list(source)[:64])
    assert catalog["missing"] == []
    assert len(catalog["messages"]) == len(source)
    provider.assert_not_called()


@pytest.mark.asyncio
async def test_current_published_translation_wins_and_stale_or_draft_is_ignored():
    version = source_version(load_catalog("en", "translation"))
    records = [
        {"locale": "fr", "namespace": "translation", "key": "language.settings", "source_version": version, "status": "published", "target_text": "Langue préférée"},
        {"locale": "fr", "namespace": "translation", "key": "language.welcome", "source_version": "old", "status": "published", "target_text": "Stale"},
        {"locale": "fr", "namespace": "translation", "key": "language.continue", "source_version": version, "status": "draft", "target_text": "Unreviewed"},
    ]
    catalog = await get_catalog(Memory(records), "fr", "translation")
    assert catalog["messages"]["language.settings"] == "Langue préférée"
    assert "Stale" not in catalog["messages"].values()
    assert "Unreviewed" not in catalog["messages"].values()


@pytest.mark.asyncio
async def test_unknown_keys_and_namespaces_are_not_sent_to_provider(monkeypatch):
    provider = AsyncMock()
    monkeypatch.setattr("server.app.i18n.catalogs.translate_messages", provider)
    with pytest.raises(HTTPException):
        await prepare_catalog_batch(Memory(), "de", "ui", ["private learner text"])
    with pytest.raises(HTTPException):
        await get_catalog(Memory(), "fr", "../../private")
    provider.assert_not_called()


def test_bad_provider_output_is_rejected():
    for output in ({"a": "Hola"}, {"a": "Hola {{name}}", "extra": "No"}, {"a": ""}):
        with pytest.raises(TranslationProviderError):
            validate_messages({"a": "Hello {{name}}"}, output)
