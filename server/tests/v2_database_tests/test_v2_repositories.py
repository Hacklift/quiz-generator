import pytest

from ...app.db.v2.models.quiz_models import QuizDocumentV2, QuizMetadataUpdateV2
from ...app.db.v2.models.reference_models import (
    FolderDocumentV2,
    FolderItemDocumentV2,
    QuizHistoryDocumentV2,
    SavedQuizDocumentV2,
)
from ...app.db.v2.repositories.quiz_repository import QuizV2Repository
from ...app.db.v2.repositories.reference_repository import ReferenceV2Repository


@pytest.mark.asyncio
async def test_quiz_v2_repository_insert_and_get(test_db):
    repository = QuizV2Repository(test_db["quizzes_v2"])
    document = QuizDocumentV2(
        title="Repository insert",
        quiz_type="multichoice",
        source="manual",
        questions=[
            {
                "question": "What is MongoDB?",
                "options": ["Relational", "Document"],
                "correct_answer": "Document",
            }
        ],
    )

    created = await repository.insert_quiz(document)
    fetched = await repository.find_by_id(str(created.id))

    assert fetched is not None
    assert fetched.title == "Repository insert"


@pytest.mark.asyncio
async def test_quiz_v2_repository_update_metadata(test_db):
    repository = QuizV2Repository(test_db["quizzes_v2"])
    created = await repository.insert_quiz(
        QuizDocumentV2(
            title="Original",
            quiz_type="open-ended",
            source="manual",
            questions=[
                {
                    "question": "What is scaling?",
                    "correct_answer": "Handling growth.",
                }
            ],
        )
    )

    updated = await repository.update_metadata(
        str(created.id),
        QuizMetadataUpdateV2(description="Updated", visibility="public"),
    )

    assert updated is not None
    assert updated.description == "Updated"
    assert updated.visibility == "public"


@pytest.mark.asyncio
async def test_quiz_v2_repository_soft_delete(test_db):
    repository = QuizV2Repository(test_db["quizzes_v2"])
    created = await repository.insert_quiz(
        QuizDocumentV2(
            title="Delete me",
            quiz_type="multichoice",
            source="manual",
            questions=[
                {
                    "question": "What is cleanup?",
                    "options": ["Refactor", "Ignore"],
                    "correct_answer": "Refactor",
                }
            ],
        )
    )

    deleted = await repository.soft_delete(str(created.id))

    assert deleted is not None
    assert deleted.status == "deleted"
    assert deleted.deleted_at is not None


@pytest.mark.asyncio
async def test_reference_repository_saved_quiz_soft_delete_and_revive(test_db):
    repository = ReferenceV2Repository(
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )

    saved = await repository.upsert_saved_quiz(
        SavedQuizDocumentV2(
            user_id="user-1",
            quiz_id="quiz-1",
            display_title="Saved quiz",
        ),
        revive_deleted=True,
    )

    deleted_count = await repository.delete_saved_quiz_by_id(str(saved.id), user_id="user-1")
    assert deleted_count == 1
    assert await repository.get_saved_quiz_by_id(str(saved.id), user_id="user-1") is None
    assert await repository.list_saved_quizzes_for_user("user-1") == []

    revived = await repository.upsert_saved_quiz(
        SavedQuizDocumentV2(
            user_id="user-1",
            quiz_id="quiz-1",
            display_title="Saved quiz revived",
        ),
        revive_deleted=True,
    )

    assert str(revived.id) == str(saved.id)
    assert revived.deleted_at is None
    assert revived.display_title == "Saved quiz revived"


@pytest.mark.asyncio
async def test_reference_repository_saved_quiz_legacy_upsert_preserves_deleted_state(test_db):
    repository = ReferenceV2Repository(
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )

    saved = await repository.upsert_saved_quiz(
        SavedQuizDocumentV2(
            user_id="user-legacy",
            quiz_id="quiz-legacy",
            display_title="Legacy saved",
            legacy_saved_quiz_id="legacy-saved-1",
        ),
        revive_deleted=True,
    )
    await repository.delete_saved_quiz_by_id(str(saved.id), user_id="user-legacy")

    preserved = await repository.upsert_saved_quiz(
        SavedQuizDocumentV2(
            user_id="user-legacy",
            quiz_id="quiz-legacy",
            display_title="Legacy saved updated",
            legacy_saved_quiz_id="legacy-saved-1",
        ),
    )

    assert str(preserved.id) == str(saved.id)
    assert preserved.deleted_at is not None
    assert await repository.get_saved_quiz_by_legacy_id("legacy-saved-1", user_id="user-legacy") is None


@pytest.mark.asyncio
async def test_reference_repository_folder_soft_delete_cascades_to_items_and_revives(test_db):
    repository = ReferenceV2Repository(
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )

    folder = await repository.insert_folder(
        FolderDocumentV2(
            user_id="user-folder",
            name="Backend",
        )
    )
    item = await repository.upsert_folder_item_by_legacy_id(
        FolderItemDocumentV2(
            folder_id=str(folder.id),
            quiz_id="quiz-1",
            display_title="Quiz one",
            position=0,
        ),
        revive_deleted=True,
    )

    await repository.delete_folder_by_id(str(folder.id))

    assert await repository.get_folder_by_id(str(folder.id)) is None
    assert await repository.list_folders_for_user("user-folder") == []
    assert await repository.get_folder_item_by_id(str(item.id)) is None
    assert await repository.list_folder_items_for_folder(str(folder.id)) == []

    revived_folder = await repository.insert_folder(
        FolderDocumentV2(
            user_id="user-folder",
            name="Backend",
        )
    )
    assert str(revived_folder.id) == str(folder.id)
    assert revived_folder.deleted_at is None


@pytest.mark.asyncio
async def test_reference_repository_folder_item_soft_delete_and_revive(test_db):
    repository = ReferenceV2Repository(
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )

    folder = await repository.insert_folder(FolderDocumentV2(user_id="user-folder", name="Systems"))
    item = await repository.upsert_folder_item_by_legacy_id(
        FolderItemDocumentV2(
            folder_id=str(folder.id),
            quiz_id="quiz-2",
            display_title="Quiz two",
            position=0,
        ),
        revive_deleted=True,
    )

    await repository.delete_folder_item_by_id(str(item.id))
    assert await repository.get_folder_item_by_id(str(item.id)) is None

    revived = await repository.upsert_folder_item_by_legacy_id(
        FolderItemDocumentV2(
            folder_id=str(folder.id),
            quiz_id="quiz-2",
            display_title="Quiz two revived",
            position=0,
        ),
        revive_deleted=True,
    )

    assert str(revived.id) == str(item.id)
    assert revived.deleted_at is None
    assert revived.display_title == "Quiz two revived"


@pytest.mark.asyncio
async def test_reference_repository_quiz_history_soft_delete_and_preserve_legacy_state(test_db):
    repository = ReferenceV2Repository(
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )

    history = await repository.insert_quiz_history(
        QuizHistoryDocumentV2(
            user_id="user-history",
            quiz_id="quiz-hist",
            action="generated",
            metadata={"topic": "Caching"},
            legacy_history_id="legacy-history-1",
        )
    )

    deleted_count = await repository.soft_delete_quiz_history_by_id(str(history.id), user_id="user-history")
    assert deleted_count == 1
    assert await repository.list_quiz_history_for_user("user-history") == []

    preserved = await repository.upsert_quiz_history(
        QuizHistoryDocumentV2(
            user_id="user-history",
            quiz_id="quiz-hist",
            action="generated",
            metadata={"topic": "Caching updated"},
            legacy_history_id="legacy-history-1",
        )
    )

    assert str(preserved.id) == str(history.id)
    assert preserved.deleted_at is not None
    assert await repository.list_quiz_history_for_user("user-history") == []
