import pytest
from bson import ObjectId
from datetime import datetime

from ....app.db.v2.migration.backfill_engine import (
    backfill_folders,
    backfill_quiz_history,
    backfill_quizzes,
    backfill_saved_quizzes,
    run_backfill,
    run_parity_checks,
)


@pytest.mark.asyncio
async def test_stage3_backfill_reuses_ai_origin_for_saved_history_and_folder(
    backfill_db,
    backfill_context_factory,
):
    ai_id = ObjectId()
    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Geography",
            "question_type": "multichoice",
            "difficulty_level": "easy",
            "audience_type": "students",
            "questions": [
                {
                    "question": "Capital of Kenya?",
                    "options": ["Nairobi", "Mombasa"],
                    "answer": "Nairobi",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    saved_id = ObjectId()
    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-1",
            "quiz_id": str(ai_id),
            "title": "Geography",
            "question_type": "multichoice",
            "questions": [
                {"question": "Capital of Kenya?", "options": ["Nairobi", "Mombasa"], "question_type": "multichoice"}
            ],
        }
    )
    history_id = ObjectId()
    await backfill_db["quiz_history"].insert_one(
        {
            "_id": history_id,
            "user_id": "user-1",
            "quiz_id": str(ai_id),
            "profession": "Geography",
            "question_type": "multichoice",
            "difficulty_level": "easy",
            "audience_type": "students",
            "questions": [
                {
                    "question": "Capital of Kenya?",
                    "options": ["Nairobi", "Mombasa"],
                    "answer": "Nairobi",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    folder_id = ObjectId()
    await backfill_db["folders"].insert_one(
        {
            "_id": folder_id,
            "user_id": "user-1",
            "name": "Trips",
            "quizzes": [
                {
                    "_id": "folder-item-1",
                    "original_quiz_id": str(saved_id),
                    "quiz_id": str(ai_id),
                    "questions": [
                        {"question": "Capital of Kenya?", "options": ["Nairobi", "Mombasa"], "question_type": "multichoice"}
                    ],
                    "question_type": "multichoice",
                    "title": "Geography",
                }
            ],
        }
    )
    context = backfill_context_factory()
    await backfill_quizzes(context)
    await backfill_saved_quizzes(context)
    await backfill_quiz_history(context)
    await backfill_folders(context)

    canonical = await backfill_db["quizzes_v2"].find_one(
        {"legacy_source_collection": "ai_generated_quizzes", "legacy_quiz_id": str(ai_id)}
    )
    saved_v2 = await backfill_db["saved_quizzes_v2"].find_one({"user_id": "user-1"})
    history_v2 = await backfill_db["quiz_history_v2"].find_one({"legacy_history_id": str(history_id)})
    folder_item_v2 = await backfill_db["folder_items_v2"].find_one({"legacy_folder_item_id": "folder-item-1"})

    assert canonical is not None
    assert saved_v2["quiz_id"] == str(canonical["_id"])
    assert saved_v2["display_title"] == "Geography"
    assert history_v2["quiz_id"] == str(canonical["_id"])
    assert history_v2["metadata"]["source"] == "ai"
    assert history_v2["metadata"]["topic"] == "Geography"
    assert folder_item_v2["quiz_id"] == str(canonical["_id"])
    assert folder_item_v2["display_title"] == "Geography"
    assert folder_item_v2["position"] == 0


@pytest.mark.asyncio
async def test_stage3_backfill_is_idempotent(backfill_db, backfill_context_factory):
    ai_id = ObjectId()
    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Networks",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is DNS?",
                    "options": ["Name system", "Firewall"],
                    "answer": "Name system",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    context = backfill_context_factory(collections=["quizzes"], run_id="idem-1")
    await backfill_quizzes(context)
    await backfill_quizzes(context)
    assert await backfill_db["quizzes_v2"].count_documents({}) == 1


@pytest.mark.asyncio
async def test_stage3_history_rerun_counts_noop_records_as_skipped(backfill_db, backfill_context_factory):
    ai_id = ObjectId()
    history_id = ObjectId()
    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Systems Design",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is caching?",
                    "options": ["Storage", "Queue"],
                    "answer": "Storage",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    await backfill_db["quiz_history"].insert_one(
        {
            "_id": history_id,
            "user_id": "user-1",
            "quiz_id": str(ai_id),
            "profession": "Systems Design",
            "question_type": "multichoice",
            "difficulty_level": "easy",
            "audience_type": "students",
            "questions": [
                {
                    "question": "What is caching?",
                    "options": ["Storage", "Queue"],
                    "answer": "Storage",
                    "question_type": "multichoice",
                }
            ],
        }
    )

    context = backfill_context_factory(collections=["quizzes", "history"], run_id="history-rerun")
    await backfill_quizzes(context)
    first_summary = await backfill_quiz_history(context)
    second_summary = await backfill_quiz_history(context)

    assert first_summary.inserted == 1
    assert second_summary.inserted == 0
    assert second_summary.updated == 0
    assert second_summary.skipped == 1


@pytest.mark.asyncio
async def test_stage3_backfill_dry_run_does_not_write(backfill_db, backfill_context_factory):
    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ObjectId(),
            "profession": "History",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "Who built the pyramids?",
                    "options": ["Egyptians", "Romans"],
                    "answer": "Egyptians",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    context = backfill_context_factory(dry_run=True, collections=["quizzes"], run_id="dry-run")
    summary = await backfill_quizzes(context)
    assert summary.inserted == 1
    assert await backfill_db["quizzes_v2"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_stage3_parity_reports_orphaned_references(backfill_db, backfill_context_factory):
    await backfill_db["saved_quizzes_v2"].insert_one(
        {"user_id": "user-1", "quiz_id": "missing-quiz", "saved_at": __import__("datetime").datetime.utcnow()}
    )
    context = backfill_context_factory(run_id="parity-1")
    report = await run_parity_checks(context)
    assert report.sections["saved"]["orphaned_quiz_refs"] == 1


@pytest.mark.asyncio
async def test_stage3_run_backfill_returns_collection_reports(backfill_db, backfill_context_factory):
    ai_id = ObjectId()
    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Biology",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is DNA?",
                    "options": ["Acid", "Cell"],
                    "answer": "Acid",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    context = backfill_context_factory(collections=["quizzes"], run_id="full-run")
    report = await run_backfill(context)
    assert "quizzes" in report.collections
    assert report.collections["quizzes"].inserted == 1


@pytest.mark.asyncio
async def test_stage3_folder_backfill_with_structure_only_payload_does_not_crash(
    backfill_db,
    backfill_context_factory,
):
    ai_id = ObjectId()
    saved_id = ObjectId()
    folder_id = ObjectId()

    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Geography",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "Capital of Kenya?",
                    "options": ["Nairobi", "Mombasa"],
                    "answer": "Nairobi",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-1",
            "title": "Geography",
            "question_type": "multichoice",
            "questions": [
                {"question": "Capital of Kenya?", "options": ["Nairobi", "Mombasa"], "question_type": "multichoice"}
            ],
        }
    )
    await backfill_db["folders"].insert_one(
        {
            "_id": folder_id,
            "user_id": "user-1",
            "name": "Trips",
            "quizzes": [
                {
                    "_id": "folder-item-1",
                    "original_quiz_id": str(saved_id),
                    "questions": [
                        {
                            "question": "Capital of Kenya?",
                            "options": ["Nairobi", "Mombasa"],
                            "question_type": "multichoice",
                        }
                    ],
                    "question_type": "multichoice",
                    "title": "Geography",
                }
            ],
        }
    )

    context = backfill_context_factory(collections=["quizzes", "folders"], run_id="folder-structure-only")
    await backfill_quizzes(context)
    summary = await backfill_folders(context)

    assert summary.malformed == 0
    assert summary.unresolved == 0
    assert summary.inserted == 2


@pytest.mark.asyncio
async def test_stage3_folder_backfill_merges_duplicate_items_for_same_canonical_quiz(
    backfill_db,
    backfill_context_factory,
):
    ai_id = ObjectId()
    folder_id = ObjectId()

    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Geography",
            "question_type": "multichoice",
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
    await backfill_db["folders"].insert_one(
        {
            "_id": folder_id,
            "user_id": "user-russia",
            "name": "Geopolitics",
            "quizzes": [
                {
                    "_id": "folder-item-1",
                    "quiz_id": str(ai_id),
                    "title": "Russia",
                    "question_type": "multichoice",
                    "questions": [
                        {
                            "question": "What is the capital of Russia?",
                            "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                            "question_type": "multichoice",
                        }
                    ],
                },
                {
                    "_id": "folder-item-2",
                    "quiz_id": str(ai_id),
                    "title": "Russia duplicate",
                    "question_type": "multichoice",
                    "questions": [
                        {
                            "question": "What is the capital of Russia?",
                            "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                            "question_type": "multichoice",
                        }
                    ],
                },
            ],
        }
    )

    context = backfill_context_factory(collections=["quizzes", "folders"], run_id="folder-duplicate-items")
    await backfill_quizzes(context)
    summary = await backfill_folders(context)
    folder_v2 = await backfill_db["folders_v2"].find_one({"legacy_folder_id": str(folder_id)})
    folder_items = await backfill_db["folder_items_v2"].find({"folder_id": str(folder_v2["_id"])}).to_list(length=10)

    assert summary.malformed == 0
    assert summary.unresolved == 0
    assert summary.conflicts == 0
    assert len(folder_items) == 1
    assert folder_items[0]["legacy_folder_item_id"] == "folder-item-1"
    assert folder_items[0]["position"] == 0


@pytest.mark.asyncio
async def test_stage3_backfill_saved_quiz_without_answers_matches_legacy_ai_source(
    backfill_db,
    backfill_context_factory,
):
    ai_id = ObjectId()
    saved_id = ObjectId()

    await backfill_db["ai_generated_quizzes"].insert_one(
        {
            "_id": ai_id,
            "profession": "Entropy",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is entropy a measure of in a system?",
                    "options": ["Energy", "Disorder", "Temperature", "Volume"],
                    "answer": "Disorder",
                    "question_type": "multichoice",
                }
            ],
        }
    )
    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-entropy",
            "title": "Entropy Quiz",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is entropy a measure of in a system?",
                    "options": ["Energy", "Disorder", "Temperature", "Volume"],
                    "question_type": "multichoice",
                }
            ],
        }
    )

    context = backfill_context_factory(collections=["saved"], run_id="saved-legacy-structure")
    summary = await backfill_saved_quizzes(context)

    assert summary.unresolved == 0
    assert summary.conflicts == 0
    assert summary.inserted == 1

    saved_v2 = await backfill_db["saved_quizzes_v2"].find_one({"legacy_saved_quiz_id": str(saved_id)})
    canonical = await backfill_db["quizzes_v2"].find_one(
        {"legacy_source_collection": "ai_generated_quizzes", "legacy_quiz_id": str(ai_id)}
    )

    assert saved_v2 is not None
    assert canonical is not None
    assert saved_v2["quiz_id"] == str(canonical["_id"])


@pytest.mark.asyncio
async def test_stage3_backfill_saved_quiz_reports_conflict_for_multiple_legacy_matches(
    backfill_db,
    backfill_context_factory,
):
    await backfill_db["ai_generated_quizzes"].insert_many(
        [
            {
                "_id": ObjectId(),
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
            },
            {
                "_id": ObjectId(),
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
            },
        ]
    )
    saved_id = ObjectId()
    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-entropy",
            "title": "Entropy Quiz",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is entropy?",
                    "options": ["Order", "Disorder"],
                    "question_type": "multichoice",
                }
            ],
        }
    )

    context = backfill_context_factory(collections=["saved"], run_id="saved-conflict")
    summary = await backfill_saved_quizzes(context)

    assert summary.inserted == 0
    assert summary.conflicts == 1
    assert summary.unresolved == 0
    assert summary.conflict_examples[0]["record_id"] == str(saved_id)
    assert len(summary.conflict_examples[0]["candidate_ids"]) == 2
    assert await backfill_db["saved_quizzes_v2"].count_documents({}) == 0


@pytest.mark.asyncio
async def test_stage3_backfill_saved_quiz_reuses_existing_v2_question_only_match(
    backfill_db,
    backfill_context_factory,
):
    existing_quiz_id = ObjectId()
    saved_id = ObjectId()
    await backfill_db["quizzes_v2"].insert_one(
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
            "content_fingerprint": "test-content",
            "structure_fingerprint": "test-structure",
            "schema_version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )
    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-russia",
            "title": "Russia",
            "question_type": "multichoice",
            "questions": [
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
        }
    )

    context = backfill_context_factory(collections=["saved"], run_id="saved-v2-question-only")
    summary = await backfill_saved_quizzes(context)
    saved_v2 = await backfill_db["saved_quizzes_v2"].find_one({"legacy_saved_quiz_id": str(saved_id)})

    assert summary.unresolved == 0
    assert summary.conflicts == 0
    assert summary.inserted == 1
    assert saved_v2 is not None
    assert saved_v2["quiz_id"] == str(existing_quiz_id)


@pytest.mark.asyncio
async def test_stage3_history_prefers_profession_over_generic_quiz_name_when_creating_canonical(
    backfill_db,
    backfill_context_factory,
):
    history_id = ObjectId()
    await backfill_db["quiz_history"].insert_one(
        {
            "_id": history_id,
            "user_id": "user-russia",
            "quiz_name": "multichoice Quiz",
            "profession": "Russia",
            "question_type": "multichoice",
            "difficulty_level": "easy",
            "audience_type": "students",
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

    context = backfill_context_factory(collections=["history"], run_id="history-generic-title")
    summary = await backfill_quiz_history(context)
    history_v2 = await backfill_db["quiz_history_v2"].find_one({"legacy_history_id": str(history_id)})
    canonical = await backfill_db["quizzes_v2"].find_one({"_id": ObjectId(history_v2["quiz_id"])})

    assert summary.inserted == 1
    assert history_v2 is not None
    assert canonical["title"] == "Russia"


@pytest.mark.asyncio
async def test_stage3_saved_backfill_updates_existing_legacy_reference_in_place_when_canonical_changes(
    backfill_db,
    backfill_context_factory,
):
    old_quiz_id = ObjectId()
    new_quiz_id = ObjectId()
    saved_id = ObjectId()
    now = datetime.utcnow()

    await backfill_db["quizzes_v2"].insert_many(
        [
            {
                "_id": old_quiz_id,
                "title": "multichoice Quiz",
                "quiz_type": "multichoice",
                "questions": [
                    {
                        "question": "What is the capital of Russia?",
                        "correct_answer": "B) Moscow",
                        "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    }
                ],
                "description": "Geopolitical power",
                "owner_user_id": None,
                "visibility": "private",
                "status": "active",
                "source": "legacy",
                "tags": [],
                "legacy_source_collection": None,
                "legacy_quiz_id": None,
                "content_fingerprint": "old-content",
                "structure_fingerprint": "old-structure",
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": new_quiz_id,
                "title": "Russia",
                "quiz_type": "multichoice",
                "questions": [
                    {
                        "question": "What is the capital of Russia?",
                        "correct_answer": "B) Moscow",
                        "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    }
                ],
                "description": "Geopolitical power",
                "owner_user_id": None,
                "visibility": "private",
                "status": "active",
                "source": "legacy",
                "tags": [],
                "legacy_source_collection": None,
                "legacy_quiz_id": None,
                "content_fingerprint": "new-content",
                "structure_fingerprint": "new-structure",
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-russia",
            "title": "Russia",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is the capital of Russia?",
                    "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    "question_type": "multichoice",
                }
            ],
        }
    )
    await backfill_db["saved_quizzes_v2"].insert_one(
        {
            "_id": ObjectId(),
            "user_id": "user-russia",
            "quiz_id": str(old_quiz_id),
            "legacy_saved_quiz_id": str(saved_id),
            "saved_at": now,
        }
    )

    context = backfill_context_factory(collections=["saved"], run_id="saved-legacy-id-upsert")
    summary = await backfill_saved_quizzes(context)
    rows = await backfill_db["saved_quizzes_v2"].find({"legacy_saved_quiz_id": str(saved_id)}).to_list(length=10)

    assert summary.inserted == 0
    assert summary.updated == 1
    assert len(rows) == 1
    assert rows[0]["quiz_id"] == str(new_quiz_id)


@pytest.mark.asyncio
async def test_stage3_saved_backfill_merges_existing_duplicate_saved_rows(
    backfill_db,
    backfill_context_factory,
):
    old_quiz_id = ObjectId()
    new_quiz_id = ObjectId()
    saved_id = ObjectId()
    now = datetime.utcnow()

    await backfill_db["quizzes_v2"].insert_many(
        [
            {
                "_id": old_quiz_id,
                "title": "multichoice Quiz",
                "quiz_type": "multichoice",
                "questions": [
                    {
                        "question": "What is the capital of Russia?",
                        "correct_answer": "B) Moscow",
                        "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    }
                ],
                "description": "Geopolitical power",
                "owner_user_id": None,
                "visibility": "private",
                "status": "active",
                "source": "legacy",
                "tags": [],
                "legacy_source_collection": None,
                "legacy_quiz_id": None,
                "content_fingerprint": "merge-old-content",
                "structure_fingerprint": "merge-old-structure",
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
            },
            {
                "_id": new_quiz_id,
                "title": "Russia",
                "quiz_type": "multichoice",
                "questions": [
                    {
                        "question": "What is the capital of Russia?",
                        "correct_answer": "B) Moscow",
                        "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    }
                ],
                "description": "Geopolitical power",
                "owner_user_id": None,
                "visibility": "private",
                "status": "active",
                "source": "legacy",
                "tags": [],
                "legacy_source_collection": None,
                "legacy_quiz_id": None,
                "content_fingerprint": "merge-new-content",
                "structure_fingerprint": "merge-new-structure",
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    await backfill_db["saved_quizzes"].insert_one(
        {
            "_id": saved_id,
            "user_id": "user-russia",
            "title": "Russia",
            "question_type": "multichoice",
            "questions": [
                {
                    "question": "What is the capital of Russia?",
                    "options": ["A) Kyiv", "B) Moscow", "C) St. Petersburg", "D) Minsk"],
                    "question_type": "multichoice",
                }
            ],
        }
    )
    await backfill_db["saved_quizzes_v2"].insert_many(
        [
            {
                "_id": ObjectId(),
                "user_id": "user-russia",
                "quiz_id": str(old_quiz_id),
                "legacy_saved_quiz_id": str(saved_id),
                "saved_at": now,
            },
            {
                "_id": ObjectId(),
                "user_id": "user-russia",
                "quiz_id": str(new_quiz_id),
                "legacy_saved_quiz_id": str(saved_id),
                "saved_at": now,
            },
        ]
    )

    context = backfill_context_factory(collections=["saved"], run_id="saved-merge-duplicates")
    summary = await backfill_saved_quizzes(context)
    rows = await backfill_db["saved_quizzes_v2"].find({"legacy_saved_quiz_id": str(saved_id)}).to_list(length=10)

    assert summary.inserted == 0
    assert summary.updated == 1
    assert len(rows) == 1
    assert rows[0]["quiz_id"] == str(new_quiz_id)
