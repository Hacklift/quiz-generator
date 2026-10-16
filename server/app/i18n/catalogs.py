"""Versioned public UI catalogs. No learner content is accepted by this service."""
import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path

from fastapi import HTTPException
from server.app.i18n.locales import FALLBACK_LOCALES
from server.app.i18n.provider import translate_messages, TranslationProviderError

logger = logging.getLogger(__name__)
CATALOG_DIR = Path(__file__).with_name("catalog_data")
NAMESPACES = {"translation", "persona", "ui"}
_provider_slots = asyncio.Semaphore(2)


def load_catalog(locale: str, namespace: str) -> dict[str, str]:
    if namespace not in NAMESPACES:
        raise HTTPException(404, "Unknown message namespace")
    path = CATALOG_DIR / f"{namespace}.{locale}.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def source_version(messages: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def placeholders(text: str) -> list[str]:
    return sorted(re.findall(r"{{\s*([^{}]+?)\s*}}", text))


def validate_messages(source: dict[str, str], translated: dict[str, str]) -> dict[str, str]:
    if not isinstance(translated, dict) or set(translated) != set(source):
        raise TranslationProviderError("Translation returned different message IDs")
    for key, value in translated.items():
        if not isinstance(value, str) or not value.strip() or placeholders(value) != placeholders(source[key]):
            raise TranslationProviderError("Translation lost an interpolation placeholder")
    return translated


async def get_catalog(collection, locale: str, namespace: str) -> dict:
    source = load_catalog("en", namespace)
    version = source_version(source)
    # Shipped Spanish and French provide a complete offline baseline.
    messages = load_catalog(locale, namespace) if locale in FALLBACK_LOCALES else {}
    records = await collection.find({
        "locale": locale, "namespace": namespace, "source_version": version,
        "status": {"$in": ["machine", "published"]},
    }).to_list(length=20_000)
    for record in records:
        if record.get("key") in source:
            try:
                validate_messages({record["key"]: source[record["key"]]}, {record["key"]: record["target_text"]})
            except TranslationProviderError:
                continue
            messages[record["key"]] = record["target_text"]
    return {"locale": locale, "namespace": namespace, "version": version,
            "messages": messages, "missing": [key for key in source if key not in messages]}


async def prepare_catalog_batch(collection, locale: str, namespace: str, keys: list[str]) -> dict:
    from datetime import datetime, timezone
    from pymongo import UpdateOne
    source = load_catalog("en", namespace)
    if len(keys) > 64 or any(key not in source for key in keys):
        raise HTTPException(422, "Request at most 64 registered UI message IDs")
    catalog = await get_catalog(collection, locale, namespace)
    pending = {key: source[key] for key in dict.fromkeys(keys) if key in catalog["missing"]}
    if pending:
        async with _provider_slots:
            # Recheck after waiting; simultaneous viewers can share cached results.
            catalog = await get_catalog(collection, locale, namespace)
            pending = {key: text for key, text in pending.items() if key in catalog["missing"]}
            if pending:
                translated = validate_messages(pending, await translate_messages(pending, locale=locale))
                now = datetime.now(timezone.utc)
                await collection.bulk_write([
                    UpdateOne(
                        {"locale": locale, "namespace": namespace, "key": key},
                        [{"$set": {
                            "created_at": {"$ifNull": ["$created_at", now]},
                            "source_text": {"$literal": pending[key]},
                            "source_version": catalog["version"],
                            "target_text": {"$cond": [
                                {"$and": [{"$eq": ["$status", "published"]},
                                          {"$eq": ["$source_version", catalog["version"]]}]},
                                "$target_text", {"$literal": text}]},
                            "status": {"$cond": [
                                {"$and": [{"$eq": ["$status", "published"]},
                                          {"$eq": ["$source_version", catalog["version"]]}]},
                                "published", "machine"]},
                            "updated_at": now,
                        }}],
                        upsert=True,
                    ) for key, text in translated.items()
                ])
                logger.info("ui_translation_batch locale=%s namespace=%s count=%d", locale, namespace, len(translated))
    return await get_catalog(collection, locale, namespace)
