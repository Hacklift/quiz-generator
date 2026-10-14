from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, Field
from server.app.core.dependencies import get_current_user
from server.app.core.rate_limiter import limiter
from server.app.i18n.catalogs import get_catalog, prepare_catalog_batch
from server.app.i18n.provider import TranslationProviderError

from server.app.core.dependencies import get_verified_user
from server.app.i18n.locales import SupportedLocale
from server.app.i18n.translation_memory import (
    TranslationDraftRequest,
    TranslationUpsert,
    read_catalog,
    require_translation_reviewer,
    upsert_translation,
)
from server.app.i18n.provider import translate_draft
from server.app.users.models import UserOut

router = APIRouter(tags=["Translations"])


class CatalogBatch(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=64)


@router.get("/catalogs/{locale}/{namespace}")
@limiter.limit("120/minute")
async def read_runtime_catalog(locale: SupportedLocale, namespace: str, request: Request, response: Response):
    response.headers["Cache-Control"] = "public, max-age=60"
    return await get_catalog(request.app.state.translation_memory_collection, locale, namespace)


@router.post("/catalogs/{locale}/{namespace}")
@limiter.limit("30/minute")
async def translate_runtime_catalog(
    locale: SupportedLocale, namespace: str, payload: CatalogBatch, request: Request,
    response: Response, current_user: UserOut = Depends(get_current_user),
):
    # Only registered UI IDs are accepted; no personal/user-generated text is sent.
    try:
        return await prepare_catalog_batch(request.app.state.translation_memory_collection, locale, namespace, payload.keys)
    except TranslationProviderError as exc:
        raise HTTPException(503, "Translations are temporarily unavailable; your language preference is saved.") from exc


@router.get("/messages/{locale}")
async def get_published_messages(locale: SupportedLocale, request: Request, namespace: str = "translation"):
    return await read_catalog(request.app.state.translation_memory_collection, locale, namespace)


@router.put("/messages", status_code=200)
async def publish_translation(
    payload: TranslationUpsert,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    require_translation_reviewer(current_user)
    return await upsert_translation(request.app.state.translation_memory_collection, payload)


@router.post("/drafts", status_code=200)
async def create_translation_draft(
    payload: TranslationDraftRequest,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    require_translation_reviewer(current_user)
    translated = await translate_draft(
        payload.source_text,
        source_locale=payload.source_locale,
        target_locale=payload.target_locale,
        glossary=payload.glossary,
        persona=payload.persona,
    )
    return await upsert_translation(
        request.app.state.translation_memory_collection,
        TranslationUpsert(
            namespace=payload.namespace,
            key=payload.key,
            source_text=payload.source_text,
            target_text=translated,
            locale=payload.target_locale,
            status="draft",
        ),
    )
