"""Gemini quiz generation, independent of UI translation and Hugging Face."""
import httpx

from server.app.core.config import settings
from server.app.quiz.utils.generation_errors import GenerationProviderError
from server.app.quiz.utils.structured_generation import parse_generated_quiz


async def generate_gemini_quiz(prompt: str, *, locale: str, question_type: str, count: int) -> dict:
    if not settings.GEMINI_API_KEY:
        raise GenerationProviderError("notConfigured")
    # Fixed provider origin; neither credentials nor endpoints come from request data.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_QUIZ_MODEL}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=settings.GEMINI_QUIZ_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers={"x-goog-api-key": settings.GEMINI_API_KEY}, json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3, "maxOutputTokens": 8192},
            })
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise GenerationProviderError("timeout") from exc
    # HTTP errors are classified by status at the route boundary without exposing bodies.
    try:
        result = response.json()
        candidate = (result.get("candidates") or [{}])[0]
        reason = candidate.get("finishReason")
        if reason != "STOP":
            raise GenerationProviderError("invalidOutput" if reason == "MAX_TOKENS" else "blocked")
        text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", []) if not part.get("thought"))
        quiz = parse_generated_quiz(text, locale=locale, question_type=question_type, count=count)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        raise GenerationProviderError("invalidOutput") from exc
    return {**quiz, "source": "gemini"}


async def generate_topic_quiz_with_gemini(payload: dict) -> dict:
    from server.app.quiz.utils.huggingface_utils import build_prompt
    locale = payload.get("content_locale") or "en"
    question_type = payload.get("question_type", "multichoice").lower()
    count = int(payload.get("num_questions", 5))
    prompt = build_prompt(payload.get("profession", "General Knowledge"), question_type,
                          payload.get("difficulty_level", "medium"), count,
                          payload.get("audience_type", "general"), payload.get("custom_instruction"), locale)
    return await generate_gemini_quiz(prompt, locale=locale, question_type=question_type, count=count)
