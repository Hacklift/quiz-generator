import importlib.util
from pathlib import Path
from typing import Any

from server.app.db.core.connection import (
    database,
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_history_v2_collection,
    get_quizzes_v2_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.quiz.repositories.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService
from server.app.quiz.services.category_taxonomy_service import (
    SEED_CATEGORIES_DIR,
    TaxonomyEntry,
    build_classification,
    display_name_from_path,
    get_taxonomy_entry,
    normalize_quiz_type,
    quiz_type_to_title,
)


QUESTION_TYPE_BY_INDEX = {
    "multiple choice": range(0, 10),
    "true or false": range(10, 20),
    "open ended": range(20, 30),
    "short answer": range(30, 40),
}


def load_questions_from_file(filepath: Path) -> list[dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("category_questions_module", filepath)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load seed questions from {filepath}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(getattr(module, "data", []))


def infer_seed_question_type(index: int) -> str:
    for question_type, question_range in QUESTION_TYPE_BY_INDEX.items():
        if index in question_range:
            return question_type
    return "multiple choice"


def group_questions_by_type(questions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, question in enumerate(questions):
        raw_question = dict(question)
        raw_type = raw_question.get("question_type") or infer_seed_question_type(index)
        canonical_type = normalize_quiz_type(str(raw_type))
        raw_question["question_type"] = canonical_type
        grouped.setdefault(canonical_type, []).append(raw_question)
    return grouped


def build_seed_title(entry: TaxonomyEntry, quiz_type: str) -> str:
    return f"{entry.subcategory}: {quiz_type_to_title(quiz_type)} Quiz"


def build_seed_description(entry: TaxonomyEntry, quiz_type: str) -> str:
    return (
        f"A {quiz_type_to_title(quiz_type).lower()} quiz covering "
        f"{entry.subcategory} in {entry.category}."
    )


class CategorySeedService:
    def __init__(self, canonical_service: CanonicalQuizWriteService | None = None):
        self.canonical_service = canonical_service or CanonicalQuizWriteService(
            QuizV2Repository(get_quizzes_v2_collection())
        )

    async def seed_all(self, base_dir: Path = SEED_CATEGORIES_DIR) -> dict[str, int]:
        await ensure_v2_collections_and_validators(database)
        await ensure_v2_indexes(
            get_quizzes_v2_collection(),
            get_folders_v2_collection(),
            get_folder_items_v2_collection(),
            get_saved_quizzes_v2_collection(),
            get_quiz_history_v2_collection(),
        )

        stats = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0}
        for category_dir in sorted(path for path in base_dir.iterdir() if path.is_dir()):
            category = display_name_from_path(category_dir.name)
            for subcategory_dir in sorted(path for path in category_dir.iterdir() if path.is_dir()):
                questions_file = subcategory_dir / "questions.py"
                if not questions_file.exists():
                    stats["skipped"] += 1
                    continue

                subcategory = display_name_from_path(subcategory_dir.name)
                entry = get_taxonomy_entry(category, subcategory)
                if not entry:
                    stats["errors"] += 1
                    continue

                try:
                    questions = load_questions_from_file(questions_file)
                    grouped = group_questions_by_type(questions)
                except Exception as exc:
                    stats["errors"] += 1
                    print(f"Failed loading category seed file {questions_file}: {exc}")
                    continue

                for quiz_type, question_group in grouped.items():
                    try:
                        _, status = await self.seed_group(entry, quiz_type, question_group)
                        stats[status] += 1
                    except Exception as exc:
                        stats["errors"] += 1
                        print(
                            "Failed seeding category quiz "
                            f"{entry.category} > {entry.subcategory} ({quiz_type}): {exc}"
                        )
        return stats

    async def seed_group(
        self,
        entry: TaxonomyEntry,
        quiz_type: str,
        questions: list[dict[str, Any]],
    ) -> tuple[Any, str]:
        classification = build_classification(
            entry,
            quiz_type,
            method="seed_path",
            confidence=1.0,
        )
        quiz_document = self.canonical_service.build_quiz_document(
            title=build_seed_title(entry, quiz_type),
            description=build_seed_description(entry, quiz_type),
            quiz_type=quiz_type,
            visibility="public",
            status="active",
            source="seed",
            questions=questions,
            tags=list(classification.tags),
            category=classification.category,
            category_slug=classification.category_slug,
            subcategory=classification.subcategory,
            subcategory_slug=classification.subcategory_slug,
            persona_category=classification.persona_category,
            classification={
                "method": classification.method,
                "confidence": classification.confidence,
            },
            legacy_source_collection="category_seed",
            legacy_quiz_id=(
                f"{classification.category_slug}:"
                f"{classification.subcategory_slug}:"
                f"{normalize_quiz_type(quiz_type)}"
            ),
        )
        return await self.canonical_service.upsert_quiz_v2_by_legacy_mapping_with_status(quiz_document)


async def seed_all_category_quizzes() -> dict[str, int]:
    return await CategorySeedService().seed_all()
