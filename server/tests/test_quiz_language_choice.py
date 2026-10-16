from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from server.app.core.config import settings
from server.app.core.dependencies import get_current_user_optional
from server.app.core.rate_limiter import limiter
from server.app.quiz.mock_data.localized_samples import get_sample_quiz
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.models.quiz_history_models import QuizHistoryModel
from server.app.quiz.models.saved_quiz_model import SavedQuizModel
from server.app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService
from server.app.quiz.utils.questions import get_questions


@pytest.mark.parametrize("locale", ["en", "es", "fr"])
@pytest.mark.parametrize("kind", ["multichoice", "true-false", "short-answer", "open-ended"])
def test_samples_are_complete_local_content(locale, kind):
    quiz = get_sample_quiz(locale, kind, 10)
    assert quiz["content_locale"] == locale and quiz["source"] == "mock"
    assert len({q["question"] for q in quiz["questions"]}) == 10
    assert all(q["answer"] and q["explanation"] for q in quiz["questions"])
    for q in quiz["questions"]:
        if kind == "multichoice":
            assert q["options"][q["correct_option_index"]] == q["answer"]
        elif kind == "true-false":
            assert q["options"][0 if q["correct_boolean"] else 1] == q["answer"]


@pytest.mark.parametrize("locale,count", [("de", 1), ("fr", 11)])
def test_missing_sample_never_changes_language_or_repeats_questions(locale, count):
    with pytest.raises(HTTPException) as error:
        get_sample_quiz(locale, "multichoice", count)
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["en", "es", "fr"])
async def test_opt_in_fallback_keeps_locale_and_is_saved_as_sample(monkeypatch, locale):
    import server.app.quiz.utils.questions as module
    monkeypatch.setattr(module, "generate_quiz_with_huggingface", AsyncMock(side_effect=RuntimeError("offline")))
    save = AsyncMock(return_value={"quiz_id": "sample-id"})
    monkeypatch.setattr(module, "save_ai_generated_quiz", save)
    payload = QuizRequest(profession="Unrelated topic", num_questions=2, question_type="multichoice",
                          difficulty_level="hard", audience_type="adults", content_locale=locale)
    with pytest.raises(HTTPException) as error:
        await get_questions(payload, user_id="user-1")
    assert error.value.status_code == 503
    save.assert_not_awaited()
    payload.allow_fallback = True
    result = await get_questions(payload, user_id="user-1")
    persisted = save.call_args.args[0]
    assert result["source"] == "mock" and result["ai_down"] is True
    assert result["content_locale"] == persisted["content_locale"] == locale
    assert persisted["source"] == "seed"
    assert result["title"] == persisted["title"] != "Unrelated topic"
    assert result["notification_message"] == result["description"]


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["es", "fr"])
async def test_standard_route_respects_explicit_choice_then_profile_default(monkeypatch, locale):
    from server.app.quiz.routes import generation as module
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(settings, "MULTILINGUAL_ENABLED", True)
    monkeypatch.setattr(settings, "MULTILINGUAL_GENERATION_ENABLED", True)
    resolve = AsyncMock(return_value="en")
    monkeypatch.setattr(module, "resolve_user_effective_locale", resolve)
    async def generate(payload, **kwargs):
        return get_sample_quiz(payload.content_locale, payload.question_type, payload.num_questions)
    monkeypatch.setattr(module, "get_questions", generate)
    app = FastAPI()
    app.state.organizations_collection = object()
    app.state.organization_memberships_collection = object()
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1", preferred_locale="en")
    app.dependency_overrides[module.get_email_service] = lambda: None
    app.include_router(module.router, prefix="/api")
    payload = dict(profession="Topic", question_type="multichoice", num_questions=1,
                   difficulty_level="easy", audience_type="students", content_locale=locale)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/get-questions", json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["content_locale"] == locale
        resolve.assert_not_awaited()
        del payload["content_locale"]
        assert (await client.post("/api/get-questions", json=payload)).json()["content_locale"] == "en"
        resolve.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["es", "fr"])
@pytest.mark.parametrize("offline", [False, True])
@pytest.mark.parametrize("provider", ["huggingface", "gemini"])
async def test_document_route_respects_choice_and_marks_opt_in_samples(monkeypatch, locale, offline, provider):
    from server.app.quiz.routes import document_quiz as module
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(settings, "MULTILINGUAL_ENABLED", True)
    monkeypatch.setattr(settings, "MULTILINGUAL_GENERATION_ENABLED", True)
    resolve = AsyncMock(return_value="en")
    monkeypatch.setattr(module, "resolve_user_effective_locale", resolve)
    monkeypatch.setattr(module, "extract_text_from_pasted_content", lambda **kw: SimpleNamespace(
        title="Input document", text="Learning material", source_document_type="text", source_document_name="notes", source_characters=100))
    monkeypatch.setattr(module, "split_text_into_chunks", lambda text: [text])
    sample = get_sample_quiz(locale, "multichoice", 1)
    generated = SimpleNamespace(title=sample["title"], description=sample["description"], questions=sample["questions"],
                                retrieved_chunks=["text"], retrieval_query="query", rag_strategy="test", embedding_cache_hit=False)
    generate = AsyncMock(side_effect=RuntimeError("offline") if offline else None, return_value=generated)
    monkeypatch.setattr(module, "generate_document_quiz_with_gemini" if provider == "gemini" else "generate_document_quiz_with_rag", generate)
    other_provider = AsyncMock(side_effect=AssertionError("The unselected provider must not run"))
    monkeypatch.setattr(module, "generate_document_quiz_with_rag" if provider == "gemini" else "generate_document_quiz_with_gemini", other_provider)
    save = AsyncMock(return_value={"quiz_id": "quiz-id"})
    monkeypatch.setattr(module, "save_ai_generated_quiz", save)
    app = FastAPI()
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1", preferred_locale="en")
    app.include_router(module.router, prefix="/api")
    payload = dict(question_type="multichoice", num_questions="1", difficulty_level="easy", audience_type="students",
                   document_text="Learning material", content_locale=locale, allow_fallback="true", ai_provider=provider)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/document-quizzes/generate", data=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["content_locale"] == locale
        assert generate.call_args.kwargs["content_locale"] == locale
        assert save.call_args.args[0]["content_locale"] == locale
        assert save.call_args.args[0]["ai_provider"] == provider
        other_provider.assert_not_awaited()
        if provider == "gemini":
            assert "token" not in generate.call_args.kwargs
        resolve.assert_not_awaited()
        assert data["source"] == ("mock" if offline else "document-rag")
        if offline:
            assert data["source_document_name"] == "" and data["retrieved_chunks"] == 0
            assert save.call_args.args[0]["source"] == "seed"
            payload["allow_fallback"] = "false"
            assert (await client.post("/api/document-quizzes/generate", data=payload)).status_code == 502


@pytest.mark.asyncio
@pytest.mark.parametrize("locale", ["es", "fr"])
async def test_saved_and_history_paths_preserve_content_without_canonical_id(locale):
    documents = {}
    saved, history = [], []
    async def insert(document):
        documents[str(document.id)] = document
        return document
    async def find(quiz_id):
        return documents.get(quiz_id)
    async def save_reference(reference, **kwargs):
        saved.append(reference)
        return reference
    async def history_reference(reference):
        history.append(reference)
        return reference
    repository = SimpleNamespace(find_or_create_by_fingerprint=insert, find_by_id=find,
                                 find_many_by_ids=AsyncMock(side_effect=lambda ids: [documents[x] for x in ids]))
    references = SimpleNamespace(upsert_saved_quiz=save_reference, insert_quiz_history=history_reference,
                                list_saved_quizzes_for_user=AsyncMock(return_value=saved),
                                list_quiz_history_for_user=AsyncMock(return_value=history))
    service = QuizUserLibraryService(canonical_service=CanonicalQuizWriteService(repository),
                                    quiz_repository=repository, reference_repository=references)
    sample = get_sample_quiz(locale, "true-false", 2)
    save_input = SavedQuizModel(title=sample["title"], description=sample["description"], question_type="true-false",
                               questions=sample["questions"], content_locale=locale)
    saved_ref = await service.create_saved_quiz(user_id="user-1", **save_input.model_dump(include={"title", "description", "question_type", "questions", "content_locale"}))
    history_input = QuizHistoryModel(user_id="user-1", quiz_name=sample["title"], question_type="true-false",
                                    questions=sample["questions"], content_locale=locale, description=sample["description"])
    await service.create_quiz_history(history_input.model_dump())
    # A later save carrying the current app language must not relabel an existing quiz.
    original = documents[saved_ref.quiz_id].model_dump()
    await service.create_saved_quiz(user_id="user-1", quiz_id=saved_ref.quiz_id, content_locale="en")
    assert documents[saved_ref.quiz_id].model_dump() == original
    saved_item = (await service.list_saved_quizzes(user_id="user-1"))[0]
    history_item = (await service.list_quiz_history_items(user_id="user-1"))[0]
    for item in (saved_item, history_item):
        assert item["content_locale"] == locale
        assert item["description"] == sample["description"]
        assert [q["question"] for q in item["questions"]] == [q["question"] for q in sample["questions"]]
        assert [q["explanation"] for q in item["questions"]] == [q["explanation"] for q in sample["questions"]]
        assert all(type(q["correct_boolean"]) is bool for q in item["questions"])
