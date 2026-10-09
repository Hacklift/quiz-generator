from fastapi import APIRouter, Depends, Request

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
