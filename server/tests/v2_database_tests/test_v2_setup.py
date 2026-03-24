import pytest

from ...app.db.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes


@pytest.mark.asyncio
async def test_v2_collection_setup_is_idempotent(test_db):
    await ensure_v2_collections_and_validators(test_db)
    await ensure_v2_collections_and_validators(test_db)

    names = set(await test_db.list_collection_names())
    assert {"quizzes_v2", "folders_v2", "folder_items_v2", "saved_quizzes_v2", "quiz_history_v2"} <= names


@pytest.mark.asyncio
async def test_v2_indexes_are_created(test_db):
    await ensure_v2_collections_and_validators(test_db)
    await ensure_v2_indexes(
        test_db["quizzes_v2"],
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )

    quizzes_indexes = await test_db["quizzes_v2"].index_information()
    saved_indexes = await test_db["saved_quizzes_v2"].index_information()

    assert "owner_user_id_1_created_at_-1" in quizzes_indexes
    assert "user_id_1_quiz_id_1" in saved_indexes


@pytest.mark.asyncio
async def test_v2_validators_reject_malformed_quiz_documents(test_db):
    await ensure_v2_collections_and_validators(test_db)

    with pytest.raises(Exception):
        await test_db["quizzes_v2"].insert_one(
            {
                "title": "Malformed quiz",
                "quiz_type": "multichoice",
                "questions": [{"question": "Missing answer"}],
            }
        )
