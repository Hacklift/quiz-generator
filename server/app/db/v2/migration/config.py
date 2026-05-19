from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from server.app.db.core.config import settings


@dataclass
class BackfillConfig:
    run_id: str
    dry_run: bool
    batch_size: int
    limit: Optional[int]
    start_after_id: Optional[str]
    collections: list[str]
    lock_lease_seconds: int

    @classmethod
    def from_settings(
        cls,
        *,
        dry_run: Optional[bool] = None,
        batch_size: Optional[int] = None,
        limit: Optional[int] = None,
        start_after_id: Optional[str] = None,
        collections: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> "BackfillConfig":
        raw_collections = collections or [
            item.strip()
            for item in settings.V2_BACKFILL_COLLECTIONS.split(",")
            if item.strip()
        ]
        generated_run_id = run_id or settings.V2_BACKFILL_RUN_ID
        if not generated_run_id:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            generated_run_id = f"stage3-{timestamp}-{uuid4().hex[:8]}"
        return cls(
            run_id=generated_run_id,
            dry_run=settings.V2_BACKFILL_DRY_RUN if dry_run is None else dry_run,
            batch_size=batch_size or settings.V2_BACKFILL_BATCH_SIZE,
            limit=settings.V2_BACKFILL_LIMIT if limit is None else limit,
            start_after_id=settings.V2_BACKFILL_START_AFTER_ID if start_after_id is None else start_after_id,
            collections=raw_collections,
            lock_lease_seconds=settings.V2_BACKFILL_LOCK_LEASE_SECONDS,
        )
