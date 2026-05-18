from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from server.app.db.crud.quiz_write_service import CanonicalQuizWriteService
from server.app.db.services.legacy_quiz_resolution_service import (
    LegacyQuizStructureConflictError,
)
from server.app.db.v2.models.reference_models import (
    FolderDocumentV2,
    FolderItemDocumentV2,
    QuizHistoryDocumentV2,
    SavedQuizDocumentV2,
)
from server.app.db.v2.repositories.quiz_repository import QuizV2Repository
from server.app.db.v2.repositories.reference_repository import ReferenceV2Repository

from .config import BackfillConfig
from .lock import MigrationLockService
from .logging import log_migration_event
from .resolver import LegacyQuizResolver
from .types import BackfillReport, CollectionMigrationSummary, ParitySummary, utcnow


@dataclass
class MigrationContext:
    config: BackfillConfig
    database: AsyncIOMotorDatabase
    canonical_service: CanonicalQuizWriteService
    reference_repository: ReferenceV2Repository
    resolver: LegacyQuizResolver
    lock_service: MigrationLockService
    report_dir: Path


def _documents_match(existing_document: dict[str, Any] | None, target_document: BaseModel) -> bool:
    if existing_document is None:
        return False
    try:
        existing_model = target_document.__class__(**existing_document)
    except Exception:
        return False
    return _normalize_for_compare(
        existing_model.model_dump(exclude={"id"})
    ) == _normalize_for_compare(target_document.model_dump(exclude={"id"}))


def _normalize_for_compare(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_for_compare(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_normalize_for_compare(item) for item in value]
    return value


def _stable_legacy_timestamp(document: dict[str, Any], *fields: str) -> datetime:
    for field in fields:
        value = document.get(field)
        if value is not None:
            return value
    legacy_id = document.get("_id")
    if isinstance(legacy_id, ObjectId):
        return legacy_id.generation_time
    return utcnow()


def build_migration_context(
    *,
    config: BackfillConfig,
    database: AsyncIOMotorDatabase,
    report_dir: Path,
) -> MigrationContext:
    quiz_repository = QuizV2Repository(database["quizzes_v2"])
    canonical_service = CanonicalQuizWriteService(quiz_repository)
    reference_repository = ReferenceV2Repository(
        database["folders_v2"],
        database["folder_items_v2"],
        database["saved_quizzes_v2"],
        database["quiz_history_v2"],
    )
    resolver = LegacyQuizResolver(
        canonical_service=canonical_service,
        ai_generated_quizzes_collection=database["ai_generated_quizzes"],
        quizzes_collection=database["quizzes"],
        saved_quizzes_collection=database["saved_quizzes"],
    )
    return MigrationContext(
        config=config,
        database=database,
        canonical_service=canonical_service,
        reference_repository=reference_repository,
        resolver=resolver,
        lock_service=MigrationLockService(database),
        report_dir=report_dir,
    )


async def iterate_batches(
    collection,
    *,
    batch_size: int,
    start_after_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> AsyncIterator[list[dict[str, Any]]]:
    processed = 0
    last_id = ObjectId(start_after_id) if start_after_id else None
    while True:
        query = {"_id": {"$gt": last_id}} if last_id is not None else {}
        remaining = None if limit is None else max(limit - processed, 0)
        if remaining == 0:
            return
        current_batch_size = batch_size if remaining is None else min(batch_size, remaining)
        cursor = collection.find(query).sort("_id", 1).limit(current_batch_size)
        documents = await cursor.to_list(length=current_batch_size)
        if not documents:
            return
        yield documents
        processed += len(documents)
        last_id = documents[-1]["_id"]


async def backfill_quizzes(context: MigrationContext) -> CollectionMigrationSummary:
    summary = CollectionMigrationSummary(
        collection="quizzes",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
        start_after_id=context.config.start_after_id,
    )

    async def process_origin_collection(collection_name: str, source_name: str, title_field: str):
        collection = context.database[collection_name]
        log_migration_event(
            "v2_backfill_collection_started",
            collection=summary.collection,
            source_collection=collection_name,
            run_id=context.config.run_id,
            dry_run=context.config.dry_run,
        )
        async for batch in iterate_batches(
            collection,
            batch_size=context.config.batch_size,
            start_after_id=context.config.start_after_id if summary.batches == 0 else None,
            limit=context.config.limit,
        ):
            summary.batches += 1
            for doc in batch:
                record_id = str(doc["_id"])
                summary.scanned += 1
                summary.last_processed_id = record_id
                try:
                    existing = await context.canonical_service.repository.find_by_legacy_mapping(
                        source_name,
                        record_id,
                    )
                    questions = doc.get("questions", [])
                    quiz_document = context.canonical_service.build_quiz_document(
                        title=doc.get(title_field) or "General Knowledge",
                        description=doc.get("custom_instruction") or doc.get("description"),
                        quiz_type=doc.get("question_type") or doc.get("quiz_type") or "multichoice",
                        owner_user_id=doc.get("user_id") or doc.get("owner_id"),
                        source="ai" if source_name == "ai_generated_quizzes" else "legacy",
                        questions=questions,
                        legacy_source_collection=source_name,
                        legacy_quiz_id=record_id,
                    )
                except Exception as exc:
                    summary.add_malformed(record_id=record_id, reason=str(exc))
                    continue

                if context.config.dry_run:
                    if existing:
                        summary.skipped += 1
                    else:
                        summary.inserted += 1
                    continue

                stored = await context.canonical_service.upsert_quiz_v2_by_legacy_mapping(quiz_document)
                if existing is None:
                    summary.inserted += 1
                elif existing.model_dump(exclude={"updated_at", "created_at"}) != stored.model_dump(
                    exclude={"updated_at", "created_at"}
                ):
                    summary.updated += 1
                else:
                    summary.skipped += 1

            await context.lock_service.renew_lock(
                migration_name="stage_3_backfill",
                run_id=context.config.run_id,
                lease_seconds=context.config.lock_lease_seconds,
            )
            log_migration_event(
                "v2_backfill_batch_completed",
                collection=summary.collection,
                batch_number=summary.batches,
                scanned=summary.scanned,
                inserted=summary.inserted,
                updated=summary.updated,
                skipped=summary.skipped,
                unresolved=summary.unresolved,
                run_id=context.config.run_id,
            )

    await process_origin_collection("ai_generated_quizzes", "ai_generated_quizzes", "profession")
    await process_origin_collection("quizzes", "quizzes", "title")
    summary.finish()
    return summary


async def backfill_saved_quizzes(context: MigrationContext) -> CollectionMigrationSummary:
    summary = CollectionMigrationSummary(
        collection="saved",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
        start_after_id=context.config.start_after_id,
    )
    collection = context.database["saved_quizzes"]
    log_migration_event(
        "v2_backfill_collection_started",
        collection=summary.collection,
        source_collection="saved_quizzes",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
    )
    async for batch in iterate_batches(
        collection,
        batch_size=context.config.batch_size,
        start_after_id=context.config.start_after_id,
        limit=context.config.limit,
    ):
        summary.batches += 1
        for doc in batch:
            record_id = str(doc["_id"])
            summary.scanned += 1
            summary.last_processed_id = record_id
            if doc.get("is_deleted"):
                summary.skipped += 1
                continue
            try:
                canonical_quiz = await context.resolver.resolve_saved_quiz(
                    doc,
                    allow_create=not context.config.dry_run,
                )
            except LegacyQuizStructureConflictError as exc:
                conflict_details = exc.to_log_fields()
                summary.add_conflict(record_id=record_id, reason=str(exc), **conflict_details)
                log_migration_event(
                    "v2_backfill_record_conflict",
                    collection=summary.collection,
                    record_id=record_id,
                    run_id=context.config.run_id,
                    **conflict_details,
                )
                continue
            except Exception as exc:
                summary.add_malformed(record_id=record_id, reason=str(exc))
                continue
            if not canonical_quiz:
                summary.add_unresolved(record_id=record_id, reason="No canonical quiz match for saved quiz")
                continue
            target_document = SavedQuizDocumentV2(
                user_id=doc["user_id"],
                quiz_id=str(canonical_quiz.id),
                display_title=doc.get("title") or canonical_quiz.title,
                legacy_saved_quiz_id=record_id,
                saved_at=_stable_legacy_timestamp(doc, "saved_at", "created_at"),
            )
            existing = await context.database["saved_quizzes_v2"].find_one(
                {"legacy_saved_quiz_id": record_id}
            )
            if context.config.dry_run:
                if existing:
                    summary.skipped += 1
                else:
                    summary.inserted += 1
                continue
            if existing is None:
                await context.reference_repository.upsert_saved_quiz(target_document)
                summary.inserted += 1
            elif _documents_match(existing, target_document):
                summary.skipped += 1
            else:
                await context.reference_repository.upsert_saved_quiz(target_document)
                summary.updated += 1
        await context.lock_service.renew_lock(
            migration_name="stage_3_backfill",
            run_id=context.config.run_id,
            lease_seconds=context.config.lock_lease_seconds,
        )
        log_migration_event(
            "v2_backfill_batch_completed",
            collection=summary.collection,
            batch_number=summary.batches,
            scanned=summary.scanned,
            inserted=summary.inserted,
            updated=summary.updated,
            skipped=summary.skipped,
            unresolved=summary.unresolved,
            run_id=context.config.run_id,
        )
    summary.finish()
    return summary


async def backfill_quiz_history(context: MigrationContext) -> CollectionMigrationSummary:
    summary = CollectionMigrationSummary(
        collection="history",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
        start_after_id=context.config.start_after_id,
    )
    collection = context.database["quiz_history"]
    log_migration_event(
        "v2_backfill_collection_started",
        collection=summary.collection,
        source_collection="quiz_history",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
    )
    async for batch in iterate_batches(
        collection,
        batch_size=context.config.batch_size,
        start_after_id=context.config.start_after_id,
        limit=context.config.limit,
    ):
        summary.batches += 1
        for doc in batch:
            record_id = str(doc["_id"])
            summary.scanned += 1
            summary.last_processed_id = record_id
            try:
                canonical_quiz = await context.resolver.resolve_quiz_history(
                    doc,
                    allow_create=not context.config.dry_run,
                )
            except LegacyQuizStructureConflictError as exc:
                conflict_details = exc.to_log_fields()
                summary.add_conflict(record_id=record_id, reason=str(exc), **conflict_details)
                log_migration_event(
                    "v2_backfill_record_conflict",
                    collection=summary.collection,
                    record_id=record_id,
                    run_id=context.config.run_id,
                    **conflict_details,
                )
                continue
            except Exception as exc:
                summary.add_malformed(record_id=record_id, reason=str(exc))
                continue
            if not canonical_quiz:
                summary.add_unresolved(record_id=record_id, reason="No canonical quiz match for history")
                continue
            target_document = QuizHistoryDocumentV2(
                user_id=doc["user_id"],
                quiz_id=str(canonical_quiz.id),
                action="generated",
                metadata={
                    "source": canonical_quiz.source,
                    "topic": doc.get("profession") or canonical_quiz.title,
                    "difficulty_level": doc.get("difficulty_level"),
                    "audience_type": doc.get("audience_type"),
                },
                legacy_history_id=record_id,
                created_at=_stable_legacy_timestamp(doc, "created_at"),
            )
            existing = await context.database["quiz_history_v2"].find_one({"legacy_history_id": record_id})
            if context.config.dry_run:
                if existing:
                    summary.skipped += 1
                else:
                    summary.inserted += 1
                continue
            if existing is None:
                await context.reference_repository.upsert_quiz_history(target_document)
                summary.inserted += 1
            elif _documents_match(existing, target_document):
                summary.skipped += 1
            else:
                await context.reference_repository.upsert_quiz_history(target_document)
                summary.updated += 1
        await context.lock_service.renew_lock(
            migration_name="stage_3_backfill",
            run_id=context.config.run_id,
            lease_seconds=context.config.lock_lease_seconds,
        )
        log_migration_event(
            "v2_backfill_batch_completed",
            collection=summary.collection,
            batch_number=summary.batches,
            scanned=summary.scanned,
            inserted=summary.inserted,
            updated=summary.updated,
            skipped=summary.skipped,
            unresolved=summary.unresolved,
            run_id=context.config.run_id,
        )
    summary.finish()
    return summary


async def backfill_folders(context: MigrationContext) -> CollectionMigrationSummary:
    summary = CollectionMigrationSummary(
        collection="folders",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
        start_after_id=context.config.start_after_id,
    )
    folders_collection = context.database["folders"]
    log_migration_event(
        "v2_backfill_collection_started",
        collection=summary.collection,
        source_collection="folders",
        run_id=context.config.run_id,
        dry_run=context.config.dry_run,
    )
    async for batch in iterate_batches(
        folders_collection,
        batch_size=context.config.batch_size,
        start_after_id=context.config.start_after_id,
        limit=context.config.limit,
    ):
        summary.batches += 1
        for folder in batch:
            folder_id = str(folder["_id"])
            summary.scanned += 1
            summary.last_processed_id = folder_id
            existing_folder = await context.reference_repository.get_folder_by_legacy_id(folder_id)
            target_folder_created_at = _stable_legacy_timestamp(folder, "created_at")
            target_folder = FolderDocumentV2(
                user_id=folder["user_id"],
                name=folder["name"],
                description=folder.get("description"),
                legacy_folder_id=folder_id,
                created_at=target_folder_created_at,
                updated_at=folder.get("updated_at") or target_folder_created_at,
            )
            if not context.config.dry_run:
                if existing_folder is None:
                    folder_v2 = await context.reference_repository.upsert_folder_by_legacy_id(target_folder)
                    summary.inserted += 1
                elif _documents_match(existing_folder.model_dump(by_alias=True), target_folder):
                    folder_v2 = existing_folder
                    summary.skipped += 1
                else:
                    folder_v2 = await context.reference_repository.upsert_folder_by_legacy_id(target_folder)
                    summary.updated += 1
            else:
                folder_v2 = existing_folder or target_folder
                if existing_folder:
                    summary.skipped += 1
                else:
                    summary.inserted += 1
            for position, item in enumerate(folder.get("quizzes", [])):
                item_id = str(item.get("_id"))
                try:
                    canonical_quiz = await context.resolver.resolve_folder_item(
                        item,
                        allow_create=not context.config.dry_run,
                    )
                except LegacyQuizStructureConflictError as exc:
                    conflict_details = exc.to_log_fields()
                    summary.add_conflict(record_id=item_id, reason=str(exc), **conflict_details)
                    log_migration_event(
                        "v2_backfill_record_conflict",
                        collection=summary.collection,
                        record_id=item_id,
                        run_id=context.config.run_id,
                        **conflict_details,
                    )
                    continue
                if not canonical_quiz:
                    summary.add_unresolved(record_id=item_id, reason="No canonical quiz match for folder item")
                    continue
                target_item = FolderItemDocumentV2(
                    folder_id=str(folder_v2.id),
                    quiz_id=str(canonical_quiz.id),
                    added_by=folder.get("user_id"),
                    position=position,
                    display_title=item.get("title") or None,
                    legacy_folder_item_id=item_id,
                    created_at=item.get("added_on")
                    or item.get("created_at")
                    or target_folder.created_at,
                )
                existing_item = await context.database["folder_items_v2"].find_one(
                    {"legacy_folder_item_id": item_id}
                )
                if context.config.dry_run:
                    if existing_item:
                        summary.skipped += 1
                    else:
                        summary.inserted += 1
                    continue
                if existing_item is None:
                    await context.reference_repository.upsert_folder_item_by_legacy_id(target_item)
                    summary.inserted += 1
                elif _documents_match(existing_item, target_item):
                    summary.skipped += 1
                else:
                    await context.reference_repository.upsert_folder_item_by_legacy_id(target_item)
                    summary.updated += 1
        await context.lock_service.renew_lock(
            migration_name="stage_3_backfill",
            run_id=context.config.run_id,
            lease_seconds=context.config.lock_lease_seconds,
        )
        log_migration_event(
            "v2_backfill_batch_completed",
            collection=summary.collection,
            batch_number=summary.batches,
            scanned=summary.scanned,
            inserted=summary.inserted,
            updated=summary.updated,
            skipped=summary.skipped,
            unresolved=summary.unresolved,
            run_id=context.config.run_id,
        )
    summary.finish()
    return summary


async def run_backfill(context: MigrationContext) -> BackfillReport:
    report = BackfillReport(run_id=context.config.run_id, dry_run=context.config.dry_run)
    backfill_map = {
        "quizzes": backfill_quizzes,
        "saved": backfill_saved_quizzes,
        "history": backfill_quiz_history,
        "folders": backfill_folders,
    }
    for collection_name in context.config.collections:
        log_migration_event(
            "v2_backfill_runner_selected",
            requested_collection=collection_name,
            run_id=context.config.run_id,
            dry_run=context.config.dry_run,
        )
        runner = backfill_map[collection_name]
        summary = await runner(context)
        report.add_summary(summary)
    report.finish()
    return report


async def run_parity_checks(context: MigrationContext) -> ParitySummary:
    parity = ParitySummary(run_id=context.config.run_id)
    quizzes_v2 = context.database["quizzes_v2"]
    saved_v2 = context.database["saved_quizzes_v2"]
    history_v2 = context.database["quiz_history_v2"]
    folders_v2 = context.database["folders_v2"]
    folder_items_v2 = context.database["folder_items_v2"]
    legacy_folders = context.database["folders"]

    embedded_folder_items = 0
    async for folder in legacy_folders.find({}, {"quizzes": 1}):
        embedded_folder_items += len(folder.get("quizzes", []))

    parity.add_section(
        "quizzes",
        {
            "legacy_ai_generated_count": await context.database["ai_generated_quizzes"].count_documents({}),
            "legacy_manual_count": await context.database["quizzes"].count_documents({}),
            "v2_count": await quizzes_v2.count_documents({}),
        },
    )
    parity.add_section(
        "saved",
        {
            "legacy_count": await context.database["saved_quizzes"].count_documents({"is_deleted": {"$ne": True}}),
            "v2_count": await saved_v2.count_documents({}),
            "orphaned_quiz_refs": await saved_v2.count_documents(
                {"quiz_id": {"$nin": [str(doc["_id"]) async for doc in quizzes_v2.find({}, {"_id": 1})]}}
            ),
        },
    )
    v2_quiz_ids = [str(doc["_id"]) async for doc in quizzes_v2.find({}, {"_id": 1})]
    v2_folder_ids = [str(doc["_id"]) async for doc in folders_v2.find({}, {"_id": 1})]
    parity.add_section(
        "history",
        {
            "legacy_count": await context.database["quiz_history"].count_documents({}),
            "v2_count": await history_v2.count_documents({}),
            "orphaned_quiz_refs": await history_v2.count_documents({"quiz_id": {"$nin": v2_quiz_ids}}),
        },
    )
    parity.add_section(
        "folders",
        {
            "legacy_folder_count": await legacy_folders.count_documents({}),
            "legacy_embedded_item_count": embedded_folder_items,
            "v2_folder_count": await folders_v2.count_documents({}),
            "v2_folder_item_count": await folder_items_v2.count_documents({}),
            "orphaned_folder_refs": await folder_items_v2.count_documents({"folder_id": {"$nin": v2_folder_ids}}),
            "orphaned_quiz_refs": await folder_items_v2.count_documents({"quiz_id": {"$nin": v2_quiz_ids}}),
        },
    )
    parity.finish()
    return parity
