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

from server.app.db.services.quiz_user_library_read_service import QuizUserLibraryReadService
from server.app.db.services.shared_quiz_read_service import SharedQuizReadService
from server.app.db.v2.repositories.quiz_repository import QuizV2Repository
from server.app.db.v2.repositories.reference_repository import ReferenceV2Repository
from server.app.db.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes


@pytest_asyncio.fixture(scope="function")
async def read_cutover_db(test_db):
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
def read_service_factory(read_cutover_db):
    def factory():
        return QuizUserLibraryReadService(
            saved_quizzes_collection=read_cutover_db["saved_quizzes"],
            quiz_history_collection=read_cutover_db["quiz_history"],
            folders_collection=read_cutover_db["folders"],
            quiz_repository=QuizV2Repository(read_cutover_db["quizzes_v2"]),
            reference_repository=ReferenceV2Repository(
                read_cutover_db["folders_v2"],
                read_cutover_db["folder_items_v2"],
                read_cutover_db["saved_quizzes_v2"],
                read_cutover_db["quiz_history_v2"],
            ),
        )

    return factory


@pytest.fixture(scope="function")
def shared_read_service_factory(read_cutover_db):
    def factory():
        return SharedQuizReadService(
            quizzes_collection=read_cutover_db["quizzes"],
            ai_generated_quizzes_collection=read_cutover_db["ai_generated_quizzes"],
            saved_quizzes_collection=read_cutover_db["saved_quizzes"],
            quiz_repository=QuizV2Repository(read_cutover_db["quizzes_v2"]),
            reference_repository=ReferenceV2Repository(
                read_cutover_db["folders_v2"],
                read_cutover_db["folder_items_v2"],
                read_cutover_db["saved_quizzes_v2"],
                read_cutover_db["quiz_history_v2"],
            ),
        )

    return factory
