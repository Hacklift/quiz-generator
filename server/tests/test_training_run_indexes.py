import pytest

from server.app.db.core.connection import ensure_training_run_indexes


class FakeIndexCollection:
    def __init__(self, indexes=None):
        self.indexes = indexes or {"_id_": {"key": [("_id", 1)]}}
        self.dropped_indexes = []
        self.created_indexes = []

    async def index_information(self):
        return self.indexes

    async def drop_index(self, index_name):
        self.dropped_indexes.append(index_name)

    async def create_index(self, keys, **kwargs):
        self.created_indexes.append((keys, kwargs))


@pytest.mark.asyncio
async def test_training_run_index_migrates_sparse_access_codes_to_string_only_unique_index():
    runs = FakeIndexCollection(
        {
            "_id_": {"key": [("_id", 1)]},
            "access_code_1": {
                "key": [("access_code", 1)],
                "unique": True,
                "sparse": True,
            },
        }
    )
    assignments = FakeIndexCollection()
    audit_events = FakeIndexCollection()
    deliveries = FakeIndexCollection()

    await ensure_training_run_indexes(runs, assignments, audit_events, deliveries)

    assert runs.dropped_indexes == ["access_code_1"]
    keys, options = runs.created_indexes[0]
    assert keys == [("access_code", 1)]
    assert options == {
        "name": "training_run_access_code_unique",
        "unique": True,
        "partialFilterExpression": {"access_code": {"$type": "string"}},
    }


@pytest.mark.asyncio
async def test_training_run_index_does_not_replace_an_unknown_access_code_index():
    runs = FakeIndexCollection(
        {
            "_id_": {"key": [("_id", 1)]},
            "operator_access_code_index": {
                "key": [("access_code", 1)],
                "unique": True,
            },
        }
    )

    with pytest.raises(RuntimeError, match="Unexpected training_runs access_code index"):
        await ensure_training_run_indexes(
            runs,
            FakeIndexCollection(),
            FakeIndexCollection(),
            FakeIndexCollection(),
        )

    assert runs.dropped_indexes == []
