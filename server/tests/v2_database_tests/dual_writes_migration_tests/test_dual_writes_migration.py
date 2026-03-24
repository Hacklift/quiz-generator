import pytest
from bson import ObjectId

from ....app.db.core.config import settings
from ....app.db.crud import folder_crud, quiz_crud, saved_quiz_crud, update_quiz_history
from ....app.db.v2.models.quiz_models import QuizCreateV2
from ....app.db.schemas.quiz_schemas import NewQuizSchema


@pytest.mark.asyncio
async def test_dual_writes_migration_legacy_only_manual_quiz_create(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "legacy_only")

    response = await quiz_crud.create_quiz(
        dual_write_db["quizzes"],
        NewQuizSchema(
            title="Legacy only",
            description="No V2 write expected",
            quiz_type="multichoice",
            questions=[
                {
                    "question": "What is caching?",
                    "options": ["Storage", "Protocol"],
                    "answer": "Storage",
                }
            ],
        ),
    )

    assert response is not None
    assert await dual_write_db["quizzes_v2"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_dual_writes_migration_manual_quiz_create_dual_write(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    response = await quiz_crud.create_quiz(
        dual_write_db["quizzes"],
        NewQuizSchema(
            title="Dual write manual quiz",
            description="Should mirror to V2",
            quiz_type="multichoice",
            owner_id="owner-1",
            questions=[
                {
                    "question": "What does SQL stand for?",
                    "options": ["Structured Query Language", "Simple Query Logic"],
                    "correct_answer": "Structured Query Language",
                }
            ],
        ),
    )

    assert response is not None
    legacy_doc = await dual_write_db["quizzes"].find_one({"_id": ObjectId(response.id)})
    mirrored_doc = await dual_write_db["quizzes_v2"].find_one({"legacy_quiz_id": response.id})

    assert legacy_doc is not None
    assert legacy_doc["canonical_quiz_id"] == str(mirrored_doc["_id"])
    assert mirrored_doc["legacy_source_collection"] == "quizzes"


@pytest.mark.asyncio
async def test_dual_writes_migration_saved_quiz_dual_write(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    await service.mirror_ai_generated_quiz(
        "legacy-ai-quiz-1",
        {
            "_id": "legacy-ai-quiz-1",
            "user_id": "user-1",
            "profession": "Infrastructure",
            "question_type": "true-false",
            "custom_instruction": None,
            "questions": [
                {
                    "question": "Redis is in-memory.",
                    "options": ["True", "False"],
                    "answer": "True",
                    "question_type": "true-false",
                }
            ],
        },
    )

    legacy_id = await saved_quiz_crud.save_quiz(
        user_id="user-1",
        title="Saved quiz",
        question_type="true-false",
        quiz_id="legacy-ai-quiz-1",
        questions=[
            {
                "question": "Redis is in-memory.",
                "options": ["True", "False"],
                "question_type": "true-false",
            }
        ],
    )

    legacy_doc = await dual_write_db["saved_quizzes"].find_one({"_id": ObjectId(legacy_id)})
    saved_reference = await dual_write_db["saved_quizzes_v2"].find_one({"user_id": "user-1"})

    assert legacy_doc is not None
    assert legacy_doc["quiz_id"] == "legacy-ai-quiz-1"
    assert legacy_doc["is_deleted"] is False
    assert legacy_doc["canonical_quiz_id"] == saved_reference["quiz_id"]


@pytest.mark.asyncio
async def test_dual_writes_migration_saved_quiz_defaults_missing_question_type(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    await service.mirror_ai_generated_quiz(
        "legacy-ai-quiz-2",
        {
            "_id": "legacy-ai-quiz-2",
            "user_id": "user-1",
            "profession": "Databases",
            "question_type": "multichoice",
            "custom_instruction": None,
            "questions": [
                {
                    "question": "What is an index?",
                    "options": ["Lookup structure", "API route"],
                    "answer": "Lookup structure",
                    "question_type": "multichoice",
                }
            ],
        },
    )

    legacy_id = await saved_quiz_crud.save_quiz(
        user_id="user-1",
        title="Saved quiz without per-question type",
        question_type="multichoice",
        quiz_id="legacy-ai-quiz-2",
        questions=[
            {
                "question": "What is an index?",
                "options": ["Lookup structure", "API route"],
            }
        ],
    )

    legacy_doc = await dual_write_db["saved_quizzes"].find_one({"_id": ObjectId(legacy_id)})
    saved_reference = await dual_write_db["saved_quizzes_v2"].find_one({"user_id": "user-1"})

    assert legacy_doc is not None
    assert legacy_doc["questions"][0]["question_type"] == "multichoice"
    assert legacy_doc["canonical_quiz_id"] == saved_reference["quiz_id"]


@pytest.mark.asyncio
async def test_dual_writes_migration_quiz_history_dual_write(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(update_quiz_history, "quiz_history_collection", dual_write_db["quiz_history"])
    monkeypatch.setattr(update_quiz_history, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    await service.mirror_ai_generated_quiz(
        "legacy-ai-quiz-3",
        {
            "_id": "legacy-ai-quiz-3",
            "user_id": "user-2",
            "profession": "Systems Design",
            "question_type": "open-ended",
            "questions": [
                {
                    "question": "Define load balancing.",
                    "answer": "Distributing requests.",
                    "question_type": "open-ended",
                }
            ],
        }
    )

    legacy_id = await update_quiz_history.update_quiz_history(
        {
            "user_id": "user-2",
            "quiz_id": "legacy-ai-quiz-3",
            "quiz_name": "History quiz",
            "question_type": "open-ended",
            "questions": [
                {
                    "question": "Define load balancing.",
                    "answer": "Distributing requests.",
                    "question_type": "open-ended",
                }
            ],
        }
    )

    legacy_doc = await dual_write_db["quiz_history"].find_one({"_id": ObjectId(legacy_id)})
    history_reference = await dual_write_db["quiz_history_v2"].find_one({"legacy_history_id": legacy_id})
    canonical_quiz = await dual_write_db["quizzes_v2"].find_one(
        {"legacy_source_collection": "ai_generated_quizzes", "legacy_quiz_id": "legacy-ai-quiz-3"}
    )

    assert legacy_doc is not None
    assert legacy_doc["quiz_id"] == "legacy-ai-quiz-3"
    assert str(canonical_quiz["_id"]) == history_reference["quiz_id"]
    assert legacy_doc["canonical_quiz_id"] == history_reference["quiz_id"]
    assert history_reference["metadata"]["source"] == "ai"
    assert history_reference["metadata"]["topic"] == "Systems Design"


@pytest.mark.asyncio
async def test_dual_writes_migration_folder_create_and_add_dual_write(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(folder_crud, "folders_collection", dual_write_db["folders"])
    monkeypatch.setattr(folder_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    await service.mirror_ai_generated_quiz(
        "legacy-ai-quiz-4",
        {
            "_id": "legacy-ai-quiz-4",
            "user_id": "user-folder",
            "profession": "Computer Science",
            "question_type": "multichoice",
            "custom_instruction": None,
            "questions": [
                {
                    "question": "What is a queue?",
                    "options": ["FIFO", "LIFO"],
                    "answer": "FIFO",
                    "question_type": "multichoice",
                }
            ],
        },
    )

    legacy_saved_id = await saved_quiz_crud.save_quiz(
        user_id="user-folder",
        title="Folder source quiz",
        question_type="multichoice",
        quiz_id="legacy-ai-quiz-4",
        questions=[
            {
                "question": "What is a queue?",
                "options": ["FIFO", "LIFO"],
                "question_type": "multichoice",
            }
        ],
    )
    saved_doc = await dual_write_db["saved_quizzes"].find_one({"_id": ObjectId(legacy_saved_id)})

    folder = await folder_crud.create_folder({"user_id": "user-folder", "name": "Backend"})
    await folder_crud.add_quiz_to_folder(
        folder["_id"],
        {
            "_id": "legacy-folder-item-1",
            "original_quiz_id": legacy_saved_id,
            "quiz_id": saved_doc["quiz_id"],
            "canonical_quiz_id": saved_doc["canonical_quiz_id"],
            "title": saved_doc["title"],
            "question_type": saved_doc["question_type"],
            "questions": saved_doc["questions"],
            "created_at": saved_doc["created_at"],
            "quiz_data": saved_doc,
        },
    )

    folder_v2 = await dual_write_db["folders_v2"].find_one({"legacy_folder_id": folder["_id"]})
    folder_item_v2 = await dual_write_db["folder_items_v2"].find_one(
        {"legacy_folder_item_id": "legacy-folder-item-1"}
    )
    canonical_quiz = await dual_write_db["quizzes_v2"].find_one(
        {"legacy_source_collection": "ai_generated_quizzes", "legacy_quiz_id": "legacy-ai-quiz-4"}
    )

    assert folder_v2 is not None
    assert folder_item_v2 is not None
    assert folder_item_v2["quiz_id"] == str(canonical_quiz["_id"])
    assert folder_item_v2["quiz_id"] == saved_doc["canonical_quiz_id"]
