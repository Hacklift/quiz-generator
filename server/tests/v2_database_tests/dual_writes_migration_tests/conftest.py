import os

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

from ....app.db.core.config import settings
from ....app.db.crud.quiz_write_service import CanonicalQuizWriteService
from ....app.db.services.quiz_dual_write_service import QuizDualWriteService
from ....app.db.v2.repositories.quiz_repository import QuizV2Repository
from ....app.db.v2.repositories.reference_repository import ReferenceV2Repository
from ....app.db.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes


@pytest_asyncio.fixture(scope="function")
async def dual_write_db(test_db):
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
def dual_write_service_factory(dual_write_db):
    def factory():
        return QuizDualWriteService(
            canonical_service=CanonicalQuizWriteService(QuizV2Repository(dual_write_db["quizzes_v2"])),
            reference_repository=ReferenceV2Repository(
                dual_write_db["folders_v2"],
                dual_write_db["folder_items_v2"],
                dual_write_db["saved_quizzes_v2"],
                dual_write_db["quiz_history_v2"],
            ),
            ai_generated_quizzes_collection=dual_write_db["ai_generated_quizzes"],
            quizzes_collection=dual_write_db["quizzes"],
        )

    return factory


@pytest.fixture(scope="function", autouse=True)
def reset_write_mode(monkeypatch):
    monkeypatch.setattr(settings, "QUIZ_V2_WRITE_MODE", "legacy_only")
    monkeypatch.setattr(settings, "QUIZ_V2_FAIL_OPEN", True)
