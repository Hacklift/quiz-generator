import os
from pathlib import Path

import pytest
import pytest_asyncio

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("email_sender", "test@example.com")
os.environ.setdefault("email_password", "password")
os.environ.setdefault("email_host", "localhost")
os.environ.setdefault("email_port", "1025")
os.environ.setdefault("share_url", "http://localhost")
os.environ.setdefault("db_name", "test_db")
os.environ.setdefault("mongo_url", "mongodb://localhost:27017")

from server.scripts.migrations.v2.migration.backfill_engine import build_migration_context
from server.scripts.migrations.v2.migration.config import BackfillConfig
from ....app.quiz.repositories.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes


class _NoopMigrationLock:
    """Keeps transformation tests independent from the CLI lock lifecycle."""

    async def renew_lock(self, **_kwargs):
        return None


@pytest_asyncio.fixture(scope="function")
async def backfill_db(test_db):
    await ensure_v2_collections_and_validators(test_db)
    await ensure_v2_indexes(
        test_db["quizzes_v2"],
        test_db["folders_v2"],
        test_db["folder_items_v2"],
        test_db["saved_quizzes_v2"],
        test_db["quiz_history_v2"],
    )
    # Stage 3 migrates only legacy rows with recorded ownership evidence. In
    # production that evidence resolves through each user's personal default.
    for user_id in ("user-1", "user-entropy", "user-russia"):
        await test_db["users"].insert_one(
            {
                "_id": user_id,
                "default_organization_id": f"organization-{user_id}",
            }
        )
    return test_db


@pytest.fixture(scope="function")
def backfill_context_factory(backfill_db, tmp_path):
    def factory(*, dry_run=False, collections=None, run_id="stage3-test"):
        config = BackfillConfig.from_settings(
            dry_run=dry_run,
            collections=collections or ["quizzes", "saved", "history", "folders"],
            run_id=run_id,
            batch_size=50,
        )
        context = build_migration_context(
            config=config,
            database=backfill_db,
            report_dir=Path(tmp_path),
        )
        # Production runners acquire the lease before entering the engine.
        # These tests exercise individual transformation stages directly.
        context.lock_service = _NoopMigrationLock()
        return context

    return factory
