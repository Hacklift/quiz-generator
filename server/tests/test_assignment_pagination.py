from copy import deepcopy
from types import SimpleNamespace

from bson import ObjectId
from fastapi import HTTPException
import pytest

from server.app.assignments import repository as module
from server.app.assignments.repository import AssignmentRepository, matching_page


def identifier(value):
    return ObjectId(f"{value:024x}")


class Cursor:
    def __init__(self, rows):
        self.rows = deepcopy(rows)

    def sort(self, key, direction):
        self.rows.sort(key=lambda row: row[key], reverse=direction < 0)
        return self

    def limit(self, length):
        assert length <= 100
        self.rows = self.rows[:length]
        return self

    async def to_list(self, length):
        return self.rows[:length]


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def find(self, query, projection=None):
        self.queries.append((deepcopy(query), projection))
        def matches(row):
            for key, expected in query.items():
                actual = row.get(key)
                if isinstance(expected, dict):
                    if "$in" in expected and actual not in expected["$in"]:
                        return False
                    if "$ne" in expected and actual == expected["$ne"]:
                        return False
                    if "$lt" in expected and not actual < expected["$lt"]:
                        return False
                elif actual != expected:
                    return False
            return True
        return Cursor([row for row in self.rows if matches(row)])


@pytest.mark.asyncio
async def test_filtered_page_refills_without_skipping_lookahead(monkeypatch):
    monkeypatch.setattr(module, "FILTERED_PAGE_BATCH_SIZE", 3)
    rows = [{"_id": identifier(i), "eligible": i in {9, 5, 2}} for i in range(1, 13)]
    collection = Collection(rows)
    async def resolve(batch):
        return [row for row in batch if row["eligible"]]

    first, cursor = await matching_page(collection, {}, resolve, limit=2)
    second, final_cursor = await matching_page(collection, {}, resolve, limit=2, cursor=cursor)

    assert [row["_id"] for row in first] == [identifier(9), identifier(5)]
    assert cursor == str(identifier(5))
    assert [row["_id"] for row in second] == [identifier(2)]
    assert final_cursor is None


@pytest.mark.asyncio
async def test_scan_budget_returns_advancing_cursor_even_for_an_empty_page(monkeypatch):
    monkeypatch.setattr(module, "FILTERED_PAGE_BATCH_SIZE", 2)
    monkeypatch.setattr(module, "FILTERED_PAGE_SCAN_LIMIT", 4)
    collection = Collection([{"_id": identifier(i)} for i in range(1, 7)])
    async def resolve(batch):
        return [row for row in batch if row["_id"] == identifier(1)]

    first, cursor = await matching_page(collection, {}, resolve, limit=2)
    assert first == []
    assert cursor == str(identifier(3))
    assert len(collection.queries) == 2
    second, cursor = await matching_page(collection, {}, resolve, limit=2, cursor=cursor)
    assert second == [{"_id": identifier(1)}]
    assert cursor is None


@pytest.mark.asyncio
async def test_filtered_page_rejects_bad_cursor_before_reading():
    collection = Collection([])
    with pytest.raises(HTTPException) as error:
        await matching_page(collection, {}, None, cursor="bad")
    assert error.value.status_code == 400
    assert collection.queries == []


@pytest.mark.asyncio
async def test_recipient_directory_uses_bounded_indexable_user_batches(monkeypatch):
    monkeypatch.setattr(module, "FILTERED_PAGE_BATCH_SIZE", 2)
    users = Collection([
        {"_id": identifier(20), "username": "A", "email": "private-a@example.com"},
        {"_id": identifier(21), "full_name": "B", "status": "active"},
        {"_id": identifier(22), "username": "Deleted", "status": "deleted"},
    ])
    memberships = Collection([
        {"_id": identifier(i), "organization_id": "org-a", "status": "active", "user_id": user_id}
        for i, user_id in [(1, str(identifier(20))), (2, str(identifier(21))),
                           (3, str(identifier(22))), (4, "bad"), (5, str(identifier(23)))]] + [
        {"_id": identifier(6), "organization_id": "org-b", "status": "active", "user_id": str(identifier(20))},
    ])
    repository = AssignmentRepository(None, users, memberships, None)
    first, cursor = await repository.recipient_options("org-a", limit=1)
    second, end = await repository.recipient_options("org-a", limit=1, cursor=cursor)

    assert [row["name"] for row in first + second] == ["B", "A"]
    assert end is None
    for query, projection in users.queries:
        assert all(isinstance(value, ObjectId) for value in query["_id"]["$in"])
        assert len(query["_id"]["$in"]) <= 2
        assert projection == {"full_name": 1, "username": 1}
    assert all(query["organization_id"] == "org-a" for query, _ in memberships.queries)


@pytest.mark.asyncio
async def test_mine_refills_past_bad_foreign_and_unavailable_runs_without_reading_snapshots(monkeypatch):
    monkeypatch.setattr(module, "FILTERED_PAGE_BATCH_SIZE", 2)
    runs = Collection([
        {"_id": identifier(26), "organization_id": "org-a", "status": "open", "delivery_kind": "quiz"},
        {"_id": identifier(21), "organization_id": "org-b", "status": "open", "delivery_kind": "quiz"},
        {"_id": identifier(22), "organization_id": "org-a", "status": "deleted", "delivery_kind": "quiz"},
        {"_id": identifier(23), "organization_id": "org-a", "status": "provisioning", "delivery_kind": "quiz"},
    ])
    recipients = Collection([
        {"_id": identifier(i), "organization_id": "org-a", "recipient_user_id": "user-a",
         "delivery_kind": "quiz", "training_run_id": run_id}
        for i, run_id in [(1, str(identifier(26)).upper()), (2, str(identifier(21))),
                          (3, str(identifier(22))), (4, str(identifier(23))), (5, "bad"), (6, None)]
    ])
    repository = AssignmentRepository(SimpleNamespace(runs_collection=runs, assignments_collection=recipients), None, None, None)

    rows, cursor = await repository.my_assignments("org-a", "user-a", limit=1)

    assert len(rows) == 1
    assert rows[0]["training_run_id"] == str(identifier(26))
    assert rows[0]["_run"]["organization_id"] == "org-a"
    assert cursor is None
    assert len(recipients.queries) >= 3
    for query, projection in runs.queries:
        assert query["organization_id"] == "org-a"
        assert "quiz_snapshot" not in projection
        assert "recipient_snapshot" not in projection
