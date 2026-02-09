import os
import pytest

if not os.path.exists("/var/run/docker.sock"):
    pytest.skip(
        "Docker is not available; skipping MongoDB integration tests.",
        allow_module_level=True,
    )

import pytest_asyncio
from testcontainers.mongodb import MongoDbContainer
from motor.motor_asyncio import AsyncIOMotorClient
from ...app.databaseSeeding import seed_quizzes_collection, seed_users_collection
from ...app.seed_data import seed_quizzes, seed_user_data



@pytest.fixture(scope="session")
def mongo_container():
    with MongoDbContainer("mongo:latest") as mongo:
        yield mongo


@pytest_asyncio.fixture(scope="function")
async def motor_client(mongo_container):
    uri = mongo_container.get_connection_url()
    client = AsyncIOMotorClient(uri)
    yield client
    client.close() 


@pytest_asyncio.fixture(scope="function")
async def test_db(motor_client):
    db = motor_client.test_db 
    for name in await db.list_collection_names():
        await db.drop_collection(name)
    yield db


@pytest_asyncio.fixture(scope="function")
async def seeded_database(test_db):
    await seed_users_collection(test_db["users"], seed_user_data)
    await seed_quizzes_collection(test_db["quizzes"], seed_quizzes)
    yield test_db 


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_db_after_test(test_db):
    yield
    for name in await test_db.list_collection_names():
        await test_db.drop_collection(name)
