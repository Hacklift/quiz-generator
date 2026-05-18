import pytest
from bson import ObjectId
from datetime import datetime

from ....app.db.core.config import settings
from ....app.db.crud import ai_generated_quiz_crud, folder_crud, quiz_crud, saved_quiz_crud, update_quiz_history
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
    assert saved_reference["display_title"] == "Saved quiz"


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
    assert folder_item_v2["display_title"] == saved_doc["title"]
    assert folder_item_v2["position"] == 0


@pytest.mark.asyncio
async def test_dual_writes_migration_folder_add_merges_duplicate_items_for_same_quiz(
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
        "legacy-ai-quiz-dup-folder",
        {
            "_id": "legacy-ai-quiz-dup-folder",
            "user_id": "user-folder",
            "profession": "Russia",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is the capital of Russia?",
                    "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    "answer": "B) Moscow",
                    "question_type": "multichoice",
                }
            ],
        },
    )

    legacy_saved_id = await saved_quiz_crud.save_quiz(
        user_id="user-folder",
        title="Russia",
        question_type="multichoice",
        quiz_id="legacy-ai-quiz-dup-folder",
        questions=[
            {
                "question": "What is the capital of Russia?",
                "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                "question_type": "multichoice",
            }
        ],
    )
    saved_doc = await dual_write_db["saved_quizzes"].find_one({"_id": ObjectId(legacy_saved_id)})
    folder = await folder_crud.create_folder({"user_id": "user-folder", "name": "Geopolitics"})

    item_payload = {
        "original_quiz_id": legacy_saved_id,
        "quiz_id": saved_doc["quiz_id"],
        "canonical_quiz_id": saved_doc["canonical_quiz_id"],
        "title": saved_doc["title"],
        "question_type": saved_doc["question_type"],
        "questions": saved_doc["questions"],
        "created_at": saved_doc["created_at"],
        "quiz_data": saved_doc,
    }

    await folder_crud.add_quiz_to_folder(folder["_id"], {"_id": "legacy-folder-item-1", **item_payload})
    await folder_crud.add_quiz_to_folder(folder["_id"], {"_id": "legacy-folder-item-2", **item_payload})

    folder_v2 = await dual_write_db["folders_v2"].find_one({"legacy_folder_id": folder["_id"]})
    folder_items = await dual_write_db["folder_items_v2"].find({"folder_id": str(folder_v2["_id"])}).to_list(length=10)

    assert folder_v2 is not None
    assert len(folder_items) == 1
    assert folder_items[0]["legacy_folder_item_id"] == "legacy-folder-item-1"
    assert folder_items[0]["quiz_id"] == saved_doc["canonical_quiz_id"]
    assert folder_items[0]["position"] == 0


@pytest.mark.asyncio
async def test_dual_writes_migration_saved_quiz_without_quiz_id_reuses_legacy_ai_source(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    ai_id = ObjectId()
    await dual_write_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "user_id": "user-entropy",
            "profession": "Entropy",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is entropy?",
                    "options": ["Order", "Disorder"],
                    "answer": "Disorder",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    legacy_id = await saved_quiz_crud.save_quiz(
        user_id="user-entropy",
        title="Entropy Quiz",
        question_type="multichoice",
        questions=[
            {
                "question": "What is entropy?",
                "options": ["Order", "Disorder"],
                "question_type": "multichoice",
            }
        ],
    )

    legacy_doc = await dual_write_db["saved_quizzes"].find_one({"_id": ObjectId(legacy_id)})
    saved_reference = await dual_write_db["saved_quizzes_v2"].find_one({"legacy_saved_quiz_id": legacy_id})
    canonical = await dual_write_db["quizzes_v2"].find_one(
        {"legacy_source_collection": "ai_generated_quizzes", "legacy_quiz_id": str(ai_id)}
    )

    assert legacy_doc is not None
    assert saved_reference is not None
    assert canonical is not None
    assert legacy_doc["canonical_quiz_id"] == str(canonical["_id"])
    assert saved_reference["quiz_id"] == str(canonical["_id"])


@pytest.mark.asyncio
async def test_dual_writes_migration_saved_quiz_without_quiz_id_reuses_existing_v2_question_match(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    existing_quiz_id = ObjectId()
    await dual_write_db["quizzes_v2"].insert_one(
        {
            "_id": existing_quiz_id,
            "title": "multichoice Quiz",
            "quiz_type": "multichoice",
            "questions": [
                {
                    "question": "What is the capital of Russia?",
                    "correct_answer": "B) Moscow",
                    "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                },
                {
                    "question": "Russia is the largest country in the world by what measure?",
                    "correct_answer": "B) Land area",
                    "options": ["A) Population", "B) Land area", "C) Military size", "D) Number of cities"],
                },
            ],
            "description": "Geopolitical power",
            "owner_user_id": None,
            "visibility": "private",
            "status": "active",
            "source": "legacy",
            "tags": [],
            "legacy_source_collection": None,
            "legacy_quiz_id": None,
            "content_fingerprint": "dual-write-content",
            "structure_fingerprint": "dual-write-structure",
            "schema_version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    legacy_id = await saved_quiz_crud.save_quiz(
        user_id="user-russia",
        title="Russia",
        question_type="multichoice",
        questions=[
            {
                "question": "What is the capital of Russia?",
                "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                "question_type": "multichoice",
            },
            {
                "question": "Russia is the largest country in the world by what measure?",
                "options": ["A) Population", "B) Land area", "C) Military size", "D) Number of cities"],
                "question_type": "multichoice",
            },
        ],
    )

    legacy_doc = await dual_write_db["saved_quizzes"].find_one({"_id": ObjectId(legacy_id)})
    saved_reference = await dual_write_db["saved_quizzes_v2"].find_one({"legacy_saved_quiz_id": legacy_id})

    assert legacy_doc is not None
    assert saved_reference is not None
    assert legacy_doc["canonical_quiz_id"] == str(existing_quiz_id)
    assert saved_reference["quiz_id"] == str(existing_quiz_id)


@pytest.mark.asyncio
async def test_dual_writes_migration_history_prefers_profession_over_generic_quiz_name(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(update_quiz_history, "quiz_history_collection", dual_write_db["quiz_history"])
    monkeypatch.setattr(update_quiz_history, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "dual_write")

    legacy_id = await update_quiz_history.update_quiz_history(
        {
            "user_id": "user-russia",
            "quiz_name": "multichoice Quiz",
            "question_type": "multichoice",
            "profession": "Russia",
            "audience_type": "students",
            "difficulty_level": "easy",
            "custom_instruction": "Geopolitical power",
            "questions": [
                {
                    "question": "What is the capital of Russia?",
                    "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    "answer": "B) Moscow",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    history_reference = await dual_write_db["quiz_history_v2"].find_one({"legacy_history_id": legacy_id})
    canonical = await dual_write_db["quizzes_v2"].find_one({"_id": ObjectId(history_reference["quiz_id"])})

    assert history_reference is not None
    assert canonical["title"] == "Russia"


@pytest.mark.asyncio
async def test_stage5_saved_quiz_v2_only_writes_only_v2_records(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "v2_only")

    await dual_write_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ObjectId("690000000000000000000001"),
            "user_id": "user-v2-only",
            "profession": "Caching",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What does Redis store in memory?",
                    "options": ["Data", "Templates"],
                    "answer": "Data",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    saved_reference_obj = await saved_quiz_crud.save_quiz(
        user_id="user-v2-only",
        title="Caching Quiz",
        question_type="multichoice",
        questions=[
            {
                "question": "What does Redis store in memory?",
                "options": ["Data", "Templates"],
                "question_type": "multichoice",
            }
        ],
    )

    assert await dual_write_db["saved_quizzes"].count_documents({}) == 0

    saved_reference = await dual_write_db["saved_quizzes_v2"].find_one({"_id": saved_reference_obj.id})
    assert saved_reference is not None
    assert saved_reference["user_id"] == "user-v2-only"
    assert saved_reference["display_title"] == "Caching Quiz"


@pytest.mark.asyncio
async def test_stage5_saved_quiz_delete_soft_deletes_and_live_save_revives(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "v2_only")

    await dual_write_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ObjectId("690000000000000000000003"),
            "user_id": "user-soft-save",
            "profession": "Operating Systems",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What does CPU stand for?",
                    "options": ["Central Processing Unit", "Core Process Utility"],
                    "answer": "Central Processing Unit",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    saved_reference = await saved_quiz_crud.save_quiz(
        user_id="user-soft-save",
        title="Operating Systems",
        question_type="multichoice",
        quiz_id="690000000000000000000003",
        questions=[
            {
                "question": "What does CPU stand for?",
                "options": ["Central Processing Unit", "Core Process Utility"],
                "question_type": "multichoice",
            }
        ],
    )

    deleted = await saved_quiz_crud.delete_saved_quiz(str(saved_reference.id), "user-soft-save")
    assert deleted is True

    stored_deleted = await dual_write_db["saved_quizzes_v2"].find_one({"_id": saved_reference.id})
    assert stored_deleted is not None
    assert stored_deleted["deleted_at"] is not None

    revived = await saved_quiz_crud.save_quiz(
        user_id="user-soft-save",
        title="Operating Systems Restored",
        question_type="multichoice",
        quiz_id="690000000000000000000003",
        questions=[
            {
                "question": "What does CPU stand for?",
                "options": ["Central Processing Unit", "Core Process Utility"],
                "question_type": "multichoice",
            }
        ],
    )

    assert str(revived.id) == str(saved_reference.id)
    stored_revived = await dual_write_db["saved_quizzes_v2"].find_one({"_id": saved_reference.id})
    assert stored_revived["deleted_at"] is None
    assert stored_revived["display_title"] == "Operating Systems Restored"


@pytest.mark.asyncio
async def test_stage5_quiz_history_v2_only_writes_only_v2_records(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(update_quiz_history, "quiz_history_collection", dual_write_db["quiz_history"])
    monkeypatch.setattr(update_quiz_history, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "v2_only")

    history_reference_obj = await update_quiz_history.update_quiz_history(
        {
            "user_id": "user-history-v2",
            "quiz_name": "Queueing",
            "question_type": "open-ended",
            "profession": "Queueing",
            "questions": [
                {
                    "question": "Define a message queue.",
                    "answer": "A buffer for asynchronous processing.",
                    "question_type": "open-ended",
                }
            ],
        }
    )

    assert await dual_write_db["quiz_history"].count_documents({}) == 0

    history_reference = await dual_write_db["quiz_history_v2"].find_one({"_id": history_reference_obj.id})
    assert history_reference is not None
    assert history_reference["user_id"] == "user-history-v2"

    canonical = await dual_write_db["quizzes_v2"].find_one({"_id": ObjectId(history_reference["quiz_id"])})
    assert canonical is not None
    assert canonical["title"] == "Queueing"


@pytest.mark.asyncio
async def test_stage5_folder_v2_only_mutations_operate_without_legacy_rows(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(saved_quiz_crud, "collection", dual_write_db["saved_quizzes"])
    monkeypatch.setattr(saved_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "v2_only")

    await dual_write_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ObjectId("690000000000000000000002"),
            "user_id": "user-folder-v2",
            "profession": "Graphs",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What does BFS stand for?",
                    "options": ["Breadth-first search", "Binary file system"],
                    "answer": "Breadth-first search",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    saved_reference_obj = await saved_quiz_crud.save_quiz(
        user_id="user-folder-v2",
        title="Graphs",
        question_type="multichoice",
        quiz_id="690000000000000000000002",
        questions=[
            {
                "question": "What does BFS stand for?",
                "options": ["Breadth-first search", "Binary file system"],
                "question_type": "multichoice",
            }
        ],
    )

    saved_reference = await dual_write_db["saved_quizzes_v2"].find_one({"_id": saved_reference_obj.id})
    assert saved_reference is not None

    source_folder = await service.create_folder_v2(user_id="user-folder-v2", name="Algorithms")
    target_folder = await service.create_folder_v2(user_id="user-folder-v2", name="Interview Prep")

    _folder, folder_item = await service.add_saved_quiz_to_folder_v2(
        folder_id=str(source_folder.id),
        saved_quiz_id=str(saved_reference_obj.id),
        user_id="user-folder-v2",
    )

    assert await dual_write_db["folders"].count_documents({}) == 0
    assert await dual_write_db["folder_items_v2"].count_documents({}) == 1
    stored_item = await dual_write_db["folder_items_v2"].find_one({"_id": folder_item.id})
    assert stored_item["folder_id"] == str(source_folder.id)
    assert stored_item["display_title"] == "Graphs"

    moved = await service.move_folder_item_v2(
        folder_item_id=str(folder_item.id),
        source_folder_id=str(source_folder.id),
        target_folder_id=str(target_folder.id),
        user_id="user-folder-v2",
    )
    assert moved is True

    moved_item = await dual_write_db["folder_items_v2"].find_one({"_id": folder_item.id})
    assert moved_item["folder_id"] == str(target_folder.id)

    removed = await service.remove_folder_item_v2(
        folder_id=str(target_folder.id),
        folder_item_id=str(folder_item.id),
        user_id="user-folder-v2",
    )
    assert removed is True
    deleted_item = await dual_write_db["folder_items_v2"].find_one({"_id": folder_item.id})
    assert deleted_item is not None
    assert deleted_item["deleted_at"] is not None
    assert await dual_write_db["folders"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_stage5_folder_delete_soft_deletes_and_recreate_revives(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "v2_only")

    folder = await service.create_folder_v2(user_id="user-folder-soft", name="Networking")
    deleted = await service.delete_folder_v2(folder_id=str(folder.id), user_id="user-folder-soft")

    assert deleted is True
    stored_folder = await dual_write_db["folders_v2"].find_one({"_id": folder.id})
    assert stored_folder is not None
    assert stored_folder["deleted_at"] is not None

    revived = await service.create_folder_v2(user_id="user-folder-soft", name="Networking")

    assert str(revived.id) == str(folder.id)
    revived_folder = await dual_write_db["folders_v2"].find_one({"_id": folder.id})
    assert revived_folder["deleted_at"] is None


@pytest.mark.asyncio
async def test_stage5_ai_generated_quiz_v2_only_returns_canonical_id_and_skips_legacy_insert(
    dual_write_db,
    dual_write_service_factory,
    monkeypatch,
):
    service = dual_write_service_factory()
    monkeypatch.setattr(ai_generated_quiz_crud, "dual_write_service", service)
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "v2_only")

    result = await ai_generated_quiz_crud.save_ai_generated_quiz(
        {
            "user_id": "user-ai-v2",
            "profession": "Distributed Systems",
            "question_type": "multichoice",
            "difficulty_level": "easy",
            "num_questions": 1,
            "audience_type": "students",
            "custom_instruction": "",
            "questions": [
                {
                    "question": "What does CAP stand for?",
                    "options": ["Consistency, Availability, Partition tolerance", "Caching, Access, Persistence"],
                    "answer": "Consistency, Availability, Partition tolerance",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    assert await dual_write_db["ai_generated_quizzes"].count_documents({}) == 0
    canonical = await dual_write_db["quizzes_v2"].find_one({"_id": ObjectId(result["quiz_id"])})
    assert canonical is not None
    assert canonical["title"] == "Distributed Systems"
