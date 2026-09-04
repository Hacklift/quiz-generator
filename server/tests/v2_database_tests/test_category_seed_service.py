import pytest

from ...app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from ...app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService
from ...app.quiz.services.category_service import CategoryService
from ...app.quiz.services.category_seed_service import CategorySeedService
from ...app.quiz.services.category_taxonomy_service import get_taxonomy_entry


@pytest.mark.asyncio
async def test_category_seed_service_upserts_categorized_v2_quiz(test_db):
    service = CategorySeedService(
        CanonicalQuizWriteService(QuizV2Repository(test_db["quizzes_v2"]))
    )
    entry = get_taxonomy_entry("Science", "Biology")
    assert entry is not None

    _, first_status = await service.seed_group(
        entry,
        "short-answer",
        [
            {
                "question": "What is the basic unit of life?",
                "answer": "Cell",
                "question_type": "short-answer",
            }
        ],
    )
    _, second_status = await service.seed_group(
        entry,
        "short-answer",
        [
            {
                "question": "What is the basic unit of life?",
                "answer": "Cell",
                "question_type": "short-answer",
            }
        ],
    )

    docs = await test_db["quizzes_v2"].find({}).to_list(length=10)

    assert first_status == "created"
    assert second_status == "unchanged"
    assert len(docs) == 1
    assert docs[0]["title"] == "Biology: Short Answer Quiz"
    assert docs[0]["source"] == "seed"
    assert docs[0]["visibility"] == "public"
    assert docs[0]["category_slug"] == "science"
    assert docs[0]["subcategory_slug"] == "biology"
    assert docs[0]["classification"] == {"method": "seed_path", "confidence": 1.0}

    category_service = CategoryService(QuizV2Repository(test_db["quizzes_v2"]))

    assert await category_service.list_categories() == ["Science"]
    assert await category_service.list_subcategories("Science") == ["Biology"]
    assert await category_service.list_quiz_types("Science", "Biology") == ["short answer"]
    questions = await category_service.list_questions(
        category="Science",
        subcategory="Biology",
        question_type="short answer",
        page=1,
        page_size=10,
    )
    assert questions == [
        {
            "question": "What is the basic unit of life?",
            "answer": "Cell",
            "subcategory": "Biology",
            "question_type": "short answer",
        }
    ]

@pytest.mark.asyncio
async def test_list_categories_persona_filter_includes_untagged_quizzes(test_db):
    repository = QuizV2Repository(test_db["quizzes_v2"])
    service = CategorySeedService(CanonicalQuizWriteService(repository))

    school_entry = get_taxonomy_entry("Science", "Biology")
    corporate_entry = get_taxonomy_entry("Onboarding", "New Hire Basics")
    assert school_entry is not None
    assert corporate_entry is not None

    await service.seed_group(
        school_entry,
        "short-answer",
        [{"question": "School Q", "answer": "A", "question_type": "short-answer"}],
    )
    await service.seed_group(
        corporate_entry,
        "short-answer",
        [{"question": "Corporate Q", "answer": "A", "question_type": "short-answer"}],
    )

    # Simulate a legacy/untagged quiz that predates persona_category existing.
    await test_db["quizzes_v2"].update_one(
        {"category_slug": "science", "subcategory_slug": "biology"},
        {"$unset": {"persona_category": ""}},
    )

    category_service = CategoryService(repository)

    school_view = await category_service.list_categories(persona_category="school")
    corporate_view = await category_service.list_categories(persona_category="corporate")

    # Untagged (legacy) quizzes must still surface under any persona filter.
    assert "Science" in school_view
    assert "Onboarding" not in school_view

    assert "Onboarding" in corporate_view
    # The untagged (legacy) Science quiz is intentionally ambiguous and
    # surfaces under both persona filters, not just its original category.
    assert "Science" in corporate_view