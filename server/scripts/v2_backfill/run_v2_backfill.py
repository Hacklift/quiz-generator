from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from server.app.db.core.connection import database
from server.app.db.v2.migration.backfill_engine import build_migration_context, run_backfill
from server.app.db.v2.migration.config import BackfillConfig
from server.app.db.v2.migration.lock import MigrationLockError
from server.app.db.v2.migration.logging import log_migration_event
from server.app.db.v2.migration.summary import write_summary_json


def parse_args():
    parser = argparse.ArgumentParser(description="Run Stage 3 V2 backfill")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to V2 collections")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-after-id", type=str, default=None)
    parser.add_argument("--collections", type=str, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    return parser.parse_args()


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main():
    configure_logging()
    args = parse_args()
    config = BackfillConfig.from_settings(
        dry_run=args.dry_run if args.dry_run else None,
        batch_size=args.batch_size,
        limit=args.limit,
        start_after_id=args.start_after_id,
        collections=args.collections.split(",") if args.collections else None,
        run_id=args.run_id,
    )
    context = build_migration_context(
        config=config,
        database=database,
        report_dir=Path(__file__).resolve().parents[2] / "tmp",
    )
    try:
        await context.lock_service.acquire_lock(
            migration_name="stage_3_backfill",
            run_id=config.run_id,
            dry_run=config.dry_run,
            triggered_by="cli",
            lease_seconds=config.lock_lease_seconds,
        )
    except MigrationLockError as exc:
        raise SystemExit(str(exc)) from exc

    status = "completed"
    report = None
    try:
        log_migration_event(
            "v2_backfill_started",
            run_id=config.run_id,
            dry_run=config.dry_run,
            batch_size=config.batch_size,
            limit=config.limit,
            start_after_id=config.start_after_id,
            collections=context.config.collections,
        )
        report = await run_backfill(context)
        summary_path = context.report_dir / f"v2_backfill_summary_{config.run_id}.json"
        write_summary_json(summary_path, report.to_dict())
        log_migration_event(
            "v2_backfill_completed",
            run_id=config.run_id,
            summary_path=str(summary_path),
            collections=context.config.collections,
        )
    except Exception as exc:
        status = "failed"
        await context.lock_service.release_lock(
            migration_name="stage_3_backfill",
            run_id=config.run_id,
            status=status,
            error=str(exc),
        )
        raise
    else:
        await context.lock_service.release_lock(
            migration_name="stage_3_backfill",
            run_id=config.run_id,
            status=status,
            summary=report.to_dict() if report else None,
        )


if __name__ == "__main__":
    asyncio.run(main())
