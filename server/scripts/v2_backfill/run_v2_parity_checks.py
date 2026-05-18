from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from server.app.db.core.connection import database
from server.app.db.v2.migration.backfill_engine import build_migration_context, run_parity_checks
from server.app.db.v2.migration.config import BackfillConfig
from server.app.db.v2.migration.logging import log_migration_event
from server.app.db.v2.migration.summary import write_summary_json


def parse_args():
    parser = argparse.ArgumentParser(description="Run Stage 3 V2 parity checks")
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
    config = BackfillConfig.from_settings(run_id=args.run_id)
    context = build_migration_context(
        config=config,
        database=database,
        report_dir=Path(__file__).resolve().parents[2] / "tmp",
    )
    log_migration_event("v2_parity_check_started", run_id=config.run_id)
    report = await run_parity_checks(context)
    summary_path = context.report_dir / f"v2_parity_summary_{config.run_id}.json"
    write_summary_json(summary_path, report.to_dict())
    log_migration_event(
        "v2_parity_check_completed",
        run_id=config.run_id,
        summary_path=str(summary_path),
    )
    print(summary_path)


if __name__ == "__main__":
    asyncio.run(main())
