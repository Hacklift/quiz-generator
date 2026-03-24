import pytest

from ...app.db.v2.models.quiz_models import QuizDocumentV2, QuizMetadataUpdateV2
from ...app.db.v2.repositories.quiz_repository import QuizV2Repository


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
