import os

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from testcontainers.mongodb import MongoDbContainer

if not os.path.exists("/var/run/docker.sock"):
    pytest.skip(
        "Docker is not available; skipping V2 MongoDB tests.",
        allow_module_level=True,
    )


@pytest.fixture(scope="session")
def mongo_container():
    with MongoDbContainer("mongo:latest") as mongo:
        yield mongo


@pytest_asyncio.fixture(scope="function")
async def motor_client(mongo_container):
    client = AsyncIOMotorClient(mongo_container.get_connection_url())
    yield client
    client.close()


@pytest_asyncio.fixture(scope="function")
async def test_db(motor_client):
    db = motor_client.v2_test_db
    for name in await db.list_collection_names():
        await db.drop_collection(name)
    yield db


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_db_after_test(test_db):
    yield
    for name in await test_db.list_collection_names():
        await test_db.drop_collection(name)
