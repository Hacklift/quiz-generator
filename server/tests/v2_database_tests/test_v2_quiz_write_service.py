from datetime import datetime

import pytest

from ...app.db.crud.quiz_write_service import CanonicalQuizWriteService
from ...app.db.v2.models.quiz_models import QuizCreateV2, QuizMetadataUpdateV2, QuizQuestionsUpdateV2
from ...app.db.v2.repositories.quiz_repository import QuizV2Repository


@pytest.mark.asyncio
async def test_create_quiz_v2_stores_canonical_document(test_db):
    service = CanonicalQuizWriteService(QuizV2Repository(test_db["quizzes_v2"]))

    created = await service.create_quiz_v2(
        QuizCreateV2(
            title="  API Design  ",
            quiz_type="multichoice",
            description="Service layer test",
            owner_user_id="user-123",
            source="manual",
            tags=[" backend ", "", "api"],
            questions=[
                {
                    "question": "Which status code means created?",
                    "options": ["200", "201", "204"],
                    "correct_answer": "201",
                }
            ],
        )
    )

    assert created.title == "API Design"
    assert created.schema_version == 1
    assert created.tags == ["backend", "api"]
    assert isinstance(created.created_at, datetime)
    assert created.created_at == created.updated_at

    stored = await test_db["quizzes_v2"].find_one({"_id": created.id})
    assert stored is not None
    assert stored["questions"][0]["correct_answer"] == "201"


@pytest.mark.asyncio
async def test_update_quiz_metadata_v2_only_changes_allowed_fields(test_db):
    service = CanonicalQuizWriteService(QuizV2Repository(test_db["quizzes_v2"]))
    created = await service.create_quiz_v2(
        QuizCreateV2(
            title="Initial title",
            quiz_type="open-ended",
            source="manual",
            questions=[
                {
                    "question": "Explain idempotency.",
                    "correct_answer": "Repeated requests have the same effect.",
                }
            ],
        )
    )

    updated = await service.update_quiz_metadata_v2(
        str(created.id),
        QuizMetadataUpdateV2(title="Updated title", tags=["backend"], status="archived"),
    )

    assert updated is not None
    assert updated.title == "Updated title"
    assert updated.tags == ["backend"]
    assert updated.status == "archived"
    assert updated.questions[0].question == "Explain idempotency."
    assert updated.updated_at >= created.updated_at


@pytest.mark.asyncio
async def test_update_quiz_questions_v2_replaces_question_set(test_db):
    service = CanonicalQuizWriteService(QuizV2Repository(test_db["quizzes_v2"]))
    created = await service.create_quiz_v2(
        QuizCreateV2(
            title="Question update",
            quiz_type="true-false",
            source="manual",
            questions=[
                {
                    "question": "Python is compiled only.",
                    "options": ["True", "False"],
                    "correct_answer": "False",
                }
            ],
        )
    )

    updated = await service.update_quiz_questions_v2(
        str(created.id),
        QuizQuestionsUpdateV2(
            questions=[
                {
                    "question": "FastAPI is built on Starlette.",
                    "options": ["True", "False"],
                    "answer": "True",
                }
            ]
        ),
    )

    assert updated is not None
    assert len(updated.questions) == 1
    assert updated.questions[0].correct_answer == "True"
    assert updated.questions[0].question == "FastAPI is built on Starlette."


@pytest.mark.asyncio
async def test_soft_delete_quiz_v2_marks_quiz_as_deleted(test_db):
    service = CanonicalQuizWriteService(QuizV2Repository(test_db["quizzes_v2"]))
    created = await service.create_quiz_v2(
        QuizCreateV2(
            title="Soft delete target",
            quiz_type="multichoice",
            source="manual",
            questions=[
                {
                    "question": "Which layer owns writes?",
                    "options": ["Route", "Service", "Template"],
                    "correct_answer": "Service",
                }
            ],
        )
    )

    deleted = await service.soft_delete_quiz_v2(str(created.id))

    assert deleted is not None
    assert deleted.status == "deleted"
    assert deleted.deleted_at is not None
    assert deleted.updated_at >= created.updated_at
