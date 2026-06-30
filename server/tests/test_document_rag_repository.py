from unittest.mock import AsyncMock

import pytest

from server.app.quiz.repositories import document_rag_repository
from server.app.quiz.utils.chunk_text import TextChunk
from server.app.quiz.utils.extract_text import ExtractedDocument


@pytest.mark.asyncio
async def test_upsert_document_embeddings_avoids_conflicting_access_count_updates(
    monkeypatch,
):
    collection = AsyncMock()
    monkeypatch.setattr(
        document_rag_repository,
        "get_document_rag_cache_collection",
        lambda: collection,
    )

    document = ExtractedDocument(
        text="Caching keeps repeated document quiz generations fast.",
        source_document_name="cache-notes.txt",
        source_document_type="txt",
        title="Cache Notes",
        source_characters=53,
    )
    chunks = [
        TextChunk(
            chunk_id=0,
            content=document.text,
            char_count=len(document.text),
        )
    ]

    await document_rag_repository.upsert_document_embeddings(
        document=document,
        chunks=chunks,
        chunk_embeddings=[[0.12, 0.34, 0.56]],
        embedding_model="test-embedding-model",
        chunk_size_chars=800,
        chunk_overlap_chars=100,
        chunk_limit=12,
    )

    collection.update_one.assert_awaited_once()
    args, kwargs = collection.update_one.await_args
    _, update_doc = args

    assert kwargs["upsert"] is True
    assert update_doc["$inc"] == {"access_count": 1}
    assert "access_count" not in update_doc["$setOnInsert"]
    assert "created_at" in update_doc["$setOnInsert"]
