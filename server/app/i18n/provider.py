"""Optional translation-provider adapter used by review workers, never page renders."""
from typing import Any

import httpx

from server.app.core.config import settings
from server.app.i18n.locales import SupportedLocale


class TranslationProviderError(RuntimeError):
    pass


async def translate_draft(
    text: str,
    *,
    source_locale: SupportedLocale,
    target_locale: SupportedLocale,
    glossary: dict[str, str] | None = None,
    persona: str | None = None,
) -> str:
    if source_locale == target_locale:
        return text
    if settings.TRANSLATION_PROVIDER == "none":
        raise TranslationProviderError("No translation provider is configured")
    api_key = settings.GEMINI_API_KEY if settings.TRANSLATION_PROVIDER == "gemini" else settings.TRANSLATION_PROVIDER_API_KEY
    if settings.TRANSLATION_PROVIDER == "gemini":
        url = settings.TRANSLATION_PROVIDER_URL or (
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.TRANSLATION_MODEL}:generateContent"
        )
    else:
        url = settings.TRANSLATION_PROVIDER_URL
    if not url or not api_key:
        raise TranslationProviderError("Translation provider credentials are not configured")

    context = (
        f"Translate from {source_locale} to {target_locale}. Preserve the glossary exactly: "
        f"{glossary or {}}. Audience: learners. Persona tone: {persona or 'friendly teacher'}. "
        "Return only the translated text.\n\nText:\n" + text
    )
    payload: dict[str, Any]
    headers: dict[str, str]
    if settings.TRANSLATION_PROVIDER == "gemini":
        payload = {"contents": [{"parts": [{"text": context}]}], "generationConfig": {"temperature": 0.2}}
        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    else:
        payload = {"text": text, "source_locale": source_locale, "target_locale": target_locale,
                   "glossary": glossary or {}, "context": {"persona": persona or "friendly teacher", "audience": "learners"}}
        headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=settings.TRANSLATION_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TranslationProviderError("Translation provider request failed") from exc
    if settings.TRANSLATION_PROVIDER == "gemini":
        translated = (((result.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [{}])[0].get("text")
    else:
        translated = result.get("translated_text") if isinstance(result, dict) else None
    if not isinstance(translated, str) or not translated.strip():
        raise TranslationProviderError("Translation provider returned no translation")
    return translated.strip()
