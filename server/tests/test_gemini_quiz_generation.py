import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from server.app.core.config import settings
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils import gemini_generation as gemini
from server.app.quiz.utils.generation_errors import GenerationProviderError, generation_http_error


def quiz(locale="la", kind="multichoice"):
    question = {"question": "Quot sunt duo et duo?", "explanation": "Duo et duo quattuor sunt."}
    if kind == "multichoice":
        question.update(options=["Unum", "Duo", "Tria", "Quattuor"], correct_option_index=3)
    elif kind == "true-false":
        question.update(options=["Verum", "Falsum"], correct_boolean=True)
    else:
        question["answer"] = "Quattuor"
    return {"content_locale": locale, "title": "Exercitatio", "description": "De numeris.", "questions": [question]}


@pytest.fixture
def provider(monkeypatch):
    state = SimpleNamespace(status=200, body=None, requests=[], timeout=False)
    real_client = httpx.AsyncClient
    def handle(request):
        state.requests.append(request)
        if state.timeout:
            raise httpx.ReadTimeout("sensitive upstream details", request=request)
        return httpx.Response(state.status, json=state.body)
    monkeypatch.setattr(gemini.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-only-gemini-key")
    monkeypatch.setattr(settings, "GEMINI_QUIZ_MODEL", "test-model")
    state.body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(quiz())}]}}]}
    return state


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["la", "es", "fr"])
@pytest.mark.parametrize("kind", ["multichoice", "true-false", "short-answer", "open-ended"])
async def test_gemini_uses_server_key_and_validates_localized_quiz(provider, locale, kind):
    provider.body["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(quiz(locale, kind))
    result = await gemini.generate_topic_quiz_with_gemini({"content_locale": locale, "question_type": kind,
        "num_questions": 1, "profession": "Arithmetic", "token": "must-not-leak-hf-token"})
    assert result["source"] == "gemini" and result["content_locale"] == locale
    assert result["questions"][0]["explanation"]
    request = provider.requests[0]
    assert request.headers["x-goog-api-key"] == "test-only-gemini-key"
    assert "key=" not in str(request.url)
    payload = json.loads(request.content)
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert f"`{locale}`" in payload["contents"][0]["parts"][0]["text"]
    assert "must-not-leak" not in request.content.decode()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,code", [(401,"credentials"),(403,"credentials"),(402,"billing"),(429,"quota"),(404,"model"),(503,"unavailable")])
async def test_upstream_errors_are_specific_but_do_not_leak_secrets(provider, status, code):
    provider.status = status
    provider.body = {"error": "sensitive provider response"}
    with pytest.raises(httpx.HTTPStatusError) as caught:
        await gemini.generate_gemini_quiz("safe prompt", locale="la", question_type="multichoice", count=1)
    error = generation_http_error(caught.value, "gemini")
    assert error.detail["code"] == code
    assert "sensitive" not in str(error.detail) and "test-only-gemini-key" not in str(error.detail)
    assert len(provider.requests) == 1  # No hidden cross-provider fallback or billing retries.


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["wrong_locale", "wrong_count", "missing_explanation", "json", "blocked", "truncated"])
async def test_invalid_or_blocked_output_is_never_used(provider, bad):
    generated = quiz()
    if bad == "wrong_locale": generated["content_locale"] = "en"
    if bad == "wrong_count": generated["questions"] = []
    if bad == "missing_explanation": del generated["questions"][0]["explanation"]
    candidate = provider.body["candidates"][0]
    candidate["content"]["parts"][0]["text"] = "not JSON" if bad == "json" else json.dumps(generated)
    if bad == "blocked": candidate["finishReason"] = "SAFETY"
    if bad == "truncated": candidate["finishReason"] = "MAX_TOKENS"
    with pytest.raises(GenerationProviderError) as caught:
        await gemini.generate_gemini_quiz("safe prompt", locale="la", question_type="multichoice", count=1)
    assert caught.value.code == ("blocked" if bad == "blocked" else "invalidOutput")


@pytest.mark.asyncio
async def test_missing_key_and_timeout_are_clear(provider, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    with pytest.raises(GenerationProviderError, match="notConfigured"):
        await gemini.generate_gemini_quiz("test", locale="la", question_type="multichoice", count=1)
    assert not provider.requests
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    provider.timeout = True
    with pytest.raises(GenerationProviderError, match="timeout"):
        await gemini.generate_gemini_quiz("test", locale="la", question_type="multichoice", count=1)


@pytest.mark.asyncio
async def test_selected_gemini_never_calls_hf_and_preserves_saved_language(monkeypatch):
    from server.app.quiz.utils import questions as module
    from server.app.quiz.utils.structured_generation import parse_generated_quiz
    result = parse_generated_quiz(json.dumps(quiz()), locale="la", question_type="multichoice", count=1)
    hf = AsyncMock(side_effect=AssertionError("HF must not be called"))
    generate = AsyncMock(return_value=result)
    save = AsyncMock(return_value={"quiz_id":"latin-id"})
    monkeypatch.setattr(module, "generate_quiz_with_huggingface", hf)
    monkeypatch.setattr(module, "generate_topic_quiz_with_gemini", generate)
    monkeypatch.setattr(module, "save_ai_generated_quiz", save)
    payload = QuizRequest(profession="Math", num_questions=1, question_type="multichoice", difficulty_level="easy",
                          audience_type="students", ai_provider="gemini", content_locale="la", token="hf-token")
    response = await module.get_questions(payload, user_id="user")
    assert response["source"] == "gemini" and response["content_locale"] == "la"
    assert save.call_args.args[0]["content_locale"] == "la"
    assert save.call_args.args[0]["ai_provider"] == "gemini"
    assert save.call_args.args[0]["token"] is None
    hf.assert_not_awaited()
    generate.side_effect = GenerationProviderError("quota")
    with pytest.raises(HTTPException) as caught:
        await module.get_questions(payload)
    assert caught.value.detail["code"] == "quota"
    hf.assert_not_awaited()
    payload.content_locale = "fr"
    payload.allow_fallback = True
    assert (await module.get_questions(payload))["source"] == "mock"
    payload.content_locale = "la"
    with pytest.raises(HTTPException):
        await module.get_questions(payload)  # No English substitution for missing Latin samples.


@pytest.mark.asyncio
async def test_gemini_document_uses_bounded_context_without_hf(monkeypatch):
    from server.app.quiz.utils import ai_generate as module
    from server.app.quiz.utils.chunk_text import TextChunk
    from server.app.quiz.utils.extract_text import extract_text_from_pasted_content
    generate = AsyncMock(return_value=quiz())
    hf = AsyncMock(side_effect=AssertionError("HF must not be used"))
    monkeypatch.setattr(module, "generate_gemini_quiz", generate)
    monkeypatch.setattr(module, "resolve_document_quiz_token", hf)
    monkeypatch.setattr(module, "_resolve_chunk_embeddings", hf)
    monkeypatch.setattr(settings, "DOCUMENT_RAG_MAX_CHUNKS", 1)
    doc = extract_text_from_pasted_content(text="Two plus two equals four. " * 10, title="Math")
    response = await module.generate_document_quiz_with_gemini(document=doc,
        chunks=[TextChunk(0,"Included source text",20),TextChunk(1,"Excluded source text",20)],
        question_type="multichoice", num_questions=1, difficulty_level="easy", audience_type="students",
        custom_instruction=None, focus_topic="Addition", content_locale="la")
    assert response.rag_strategy == "bounded_document_context"
    assert len(response.retrieved_chunks) == 1
    assert "Included source text" in generate.call_args.args[0]
    assert "Excluded source text" not in generate.call_args.args[0]
    assert generate.call_args.kwargs["locale"] == "la"
    hf.assert_not_awaited()


def test_unknown_provider_is_rejected_and_old_clients_default_to_hf():
    payload = dict(profession="Math", num_questions=1, question_type="multichoice", difficulty_level="easy", audience_type="students")
    assert QuizRequest(**payload).ai_provider == "huggingface"
    with pytest.raises(ValidationError):
        QuizRequest(**payload, ai_provider="untrusted")


@pytest.mark.asyncio
async def test_saving_gemini_quiz_does_not_trigger_hf_taxonomy(monkeypatch):
    from server.app.quiz.repositories import ai_generated_quiz_repository as module
    token = AsyncMock(side_effect=AssertionError("Gemini must not resolve HF credentials"))
    classify = AsyncMock(return_value=None)
    stored = SimpleNamespace(id="quiz-id", category=None, category_slug=None,
        subcategory=None, subcategory_slug=None, tags=[], classification=None)
    service = SimpleNamespace(build_quiz_document=lambda **kwargs: kwargs,
        find_or_create_quiz_v2_by_fingerprint=AsyncMock(return_value=stored))
    monkeypatch.setattr(module, "get_user_token", token)
    monkeypatch.setattr(module, "classify_quiz_taxonomy", classify)
    monkeypatch.setattr(module, "canonical_service", service)
    response = await module.save_ai_generated_quiz({**quiz(), "user_id":"user", "ai_provider":"gemini", "question_type":"multichoice"})
    assert response["quiz_id"] == "quiz-id"
    assert classify.call_args.kwargs["use_ai"] is False
    token.assert_not_awaited()
    saved = service.find_or_create_quiz_v2_by_fingerprint.call_args.args[0]
    assert saved["content_locale"] == "la" and saved["source"] == "ai"
