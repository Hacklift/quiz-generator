import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from bson import ObjectId


@pytest.fixture
def event_loop():
  loop = asyncio.new_event_loop()
  yield loop
  loop.close()


@dataclass
class InsertResult:
  inserted_id: Any


@dataclass
class UpdateResult:
  modified_count: int = 1
  deleted_count: int = 1


class FakeCursor:
  def __init__(self, docs: List[Dict[str, Any]]):
    self._docs = docs

  def sort(self, *_args, **_kwargs):
    return self

  def skip(self, _n: int):
    return self

  def limit(self, _n: int):
    return self

  async def to_list(self, length: int | None = None):
    if length is None:
      return list(self._docs)
    return list(self._docs)[:length]


class FakeCollection:
  def __init__(self, docs: List[Dict[str, Any]] | None = None):
    self.docs = docs or []

  async def insert_one(self, doc: Dict[str, Any]):
    if "_id" not in doc:
      doc["_id"] = ObjectId()
    self.docs.append(doc)
    return InsertResult(doc["_id"])

  async def find_one(self, query: Dict[str, Any], projection: Dict[str, int] | None = None):
    for doc in self.docs:
      if _matches(doc, query):
        if projection:
          filtered = {k: v for k, v in doc.items() if k not in projection}
          return filtered
        return doc
    return None

  def find(self, query: Dict[str, Any], projection: Dict[str, int] | None = None):
    results = []
    for doc in self.docs:
      if _matches(doc, query):
        if projection:
          filtered = {k: v for k, v in doc.items() if k not in projection}
          results.append(filtered)
        else:
          results.append(doc)
    return FakeCursor(results)

  async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
    doc = await self.find_one(query)
    if not doc and upsert:
      doc = {**query}
      self.docs.append(doc)
    if not doc:
      return UpdateResult(modified_count=0, deleted_count=0)

    if "$set" in update:
      doc.update(update["$set"])
    if "$unset" in update:
      for key in update["$unset"].keys():
        doc.pop(key, None)
    if "$push" in update:
      for key, value in update["$push"].items():
        doc.setdefault(key, []).append(value)
    if "$pull" in update:
      for key, value in update["$pull"].items():
        if isinstance(value, dict) and "$in" in value:
          doc[key] = [item for item in doc.get(key, []) if item.get("_id") not in value["$in"]]
        else:
          doc[key] = [item for item in doc.get(key, []) if item.get("_id") != value.get("_id")]
    return UpdateResult(modified_count=1, deleted_count=1)

  async def delete_one(self, query: Dict[str, Any]):
    before = len(self.docs)
    self.docs = [doc for doc in self.docs if not _matches(doc, query)]
    return UpdateResult(modified_count=0, deleted_count=before - len(self.docs))

  async def delete_many(self, query: Dict[str, Any]):
    before = len(self.docs)
    self.docs = [doc for doc in self.docs if not _matches(doc, query)]
    return UpdateResult(modified_count=0, deleted_count=before - len(self.docs))

  async def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], return_document: Any = None):
    await self.update_one(query, update)
    return await self.find_one(query)


class FakeRedis:
  def __init__(self):
    self.store: Dict[str, Any] = {}

  async def setex(self, key: str, _ttl, value: Any):
    self.store[key] = value

  async def get(self, key: str):
    return self.store.get(key)

  async def delete(self, key: str):
    self.store.pop(key, None)

  async def incr(self, key: str):
    self.store[key] = int(self.store.get(key, 0)) + 1
    return self.store[key]

  async def ttl(self, key: str):
    return 600 if key in self.store else -2

  async def expire(self, _key: str, _ttl: int):
    return True


def _matches(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
  for key, value in query.items():
    if isinstance(value, dict) and "$in" in value:
      if doc.get(key) not in value["$in"]:
        return False
    elif isinstance(value, dict) and "$or" in value:
      if not any(_matches(doc, clause) for clause in value["$or"]):
        return False
    else:
      doc_value = doc.get(key)
      if isinstance(doc_value, ObjectId) and isinstance(value, str):
        if str(doc_value) != value:
          return False
        continue
      if isinstance(doc_value, str) and isinstance(value, ObjectId):
        if doc_value != str(value):
          return False
        continue
      if doc_value != value:
        return False
  return True


@pytest.fixture
def fake_users_collection():
  return FakeCollection()


@pytest.fixture
def fake_blacklist_collection():
  return FakeCollection()


@pytest.fixture
def fake_quiz_history_collection():
  return FakeCollection()


@pytest.fixture
def fake_saved_quizzes_collection():
  return FakeCollection()


@pytest.fixture
def fake_folders_collection():
  return FakeCollection()


@pytest.fixture
def fake_user_tokens_collection():
  return FakeCollection()


@pytest.fixture
def fake_redis():
  return FakeRedis()


@pytest.fixture
def dummy_user():
  return SimpleNamespace(
    id=str(ObjectId()),
    username="tester",
    email="tester@example.com",
    role="user",
    is_active=True,
    is_verified=True,
  )
