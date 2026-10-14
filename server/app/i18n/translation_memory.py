"""Approved translation-memory storage.

Provider calls are deliberately kept out of request rendering. A worker or
admin process can write drafts, reviewers publish them, and clients only read
published records.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Literal

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel, Field

from server.app.i18n.locales import SupportedLocale

logger = logging.getLogger(__name__)


class TranslationUpsert(BaseModel):
    namespace: str = Field(min_length=1, max_length=80)
    key: str = Field(min_length=1, max_length=240)
    source_text: str = Field(min_length=1, max_length=20_000)
    target_text: str = Field(min_length=1, max_length=20_000)
    locale: SupportedLocale
    status: Literal["draft", "published"] = "draft"
    glossary_version: str | None = None


class TranslationDraftRequest(BaseModel):
    namespace: str = Field(min_length=1, max_length=80)
    key: str = Field(min_length=1, max_length=240)
    source_text: str = Field(min_length=1, max_length=20_000)
    source_locale: SupportedLocale = "en"
    target_locale: SupportedLocale
    glossary: dict[str, str] = Field(default_factory=dict)
    persona: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def read_catalog(collection: AsyncIOMotorCollection, locale: SupportedLocale, namespace: str):
    cursor = collection.find({"locale": locale, "namespace": namespace, "status": "published"})
    records = await cursor.to_list(length=10_000)
    logger.info("translation_catalog_read locale=%s namespace=%s entries=%d", locale, namespace, len(records))
    return {f"{record['namespace']}:{record['key']}": record["target_text"] for record in records}


async def upsert_translation(collection: AsyncIOMotorCollection, payload: TranslationUpsert) -> dict[str, Any]:
    now = _now()
    record = payload.model_dump()
    from server.app.i18n.catalogs import load_catalog, source_version, validate_messages, NAMESPACES
    from server.app.i18n.provider import TranslationProviderError
    if payload.namespace in NAMESPACES:
        source = load_catalog("en", payload.namespace)
        if payload.key in source:
            if payload.source_text != source[payload.key]:
                raise HTTPException(409, "The source message has changed; translate the current version")
            try:
                validate_messages({payload.key: payload.source_text}, {payload.key: payload.target_text})
            except TranslationProviderError as exc:
                raise HTTPException(422, "Translation placeholders must match the source") from exc
            record["source_version"] = source_version(source)
    record.update({"updated_at": now, "reviewed_at": now if payload.status == "published" else None})
    await collection.update_one(
        {"locale": payload.locale, "namespace": payload.namespace, "key": payload.key},
        {"$set": record, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    logger.info("translation_memory_upsert locale=%s namespace=%s status=%s", payload.locale, payload.namespace, payload.status)
    return record


def require_translation_reviewer(user) -> None:
    if not user or user.role not in {"admin", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Translation reviewer access required")
