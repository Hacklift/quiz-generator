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

from ....app.db.v2.migration.backfill_engine import build_migration_context
from ....app.db.v2.migration.config import BackfillConfig
from ....app.db.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes


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
        return build_migration_context(
            config=config,
            database=backfill_db,
            report_dir=Path(tmp_path),
        )

    return factory
