from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Optional

from server.app.db.core.connection import get_document_rag_cache_collection
from server.app.quiz.utils.chunk_text import TextChunk
from server.app.quiz.utils.extract_text import ExtractedDocument


def build_document_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_cache_query(
    *,
    document_fingerprint: str,
    embedding_model: str,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    chunk_limit: int,
) -> dict[str, Any]:
    return {
        "document_fingerprint": document_fingerprint,
        "embedding_model": embedding_model,
        "chunk_size_chars": chunk_size_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "chunk_limit": chunk_limit,
    }


def _serialize_chunk_payload(
    *,
    chunk: TextChunk,
    embedding: list[float],
) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "content": chunk.content,
        "char_count": chunk.char_count,
        "embedding": embedding,
    }


def _deserialize_cached_chunks(
    payload: list[dict[str, Any]],
) -> tuple[list[TextChunk], list[list[float]]]:
    chunks: list[TextChunk] = []
    embeddings: list[list[float]] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        embedding = item.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            continue

        normalized_embedding = [
            float(value)
            for value in embedding
            if isinstance(value, (int, float))
        ]
        if not normalized_embedding:
            continue

        chunk = TextChunk(
            chunk_id=int(item.get("chunk_id", len(chunks))),
            content=str(item.get("content", "")),
            char_count=int(item.get("char_count", 0)),
        )
        if not chunk.content:
            continue

        chunks.append(chunk)
        embeddings.append(normalized_embedding)

    return chunks, embeddings


def _cached_chunks_match(
    expected_chunks: list[TextChunk],
    cached_chunks: list[TextChunk],
) -> bool:
    if len(expected_chunks) != len(cached_chunks):
        return False

    return all(
        expected.chunk_id == cached.chunk_id
        and expected.content == cached.content
        and expected.char_count == cached.char_count
        for expected, cached in zip(expected_chunks, cached_chunks)
    )


async def get_cached_document_embeddings(
    *,
    document: ExtractedDocument,
    chunks: list[TextChunk],
    embedding_model: str,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    chunk_limit: int,
) -> Optional[list[list[float]]]:
    collection = get_document_rag_cache_collection()
    document_fingerprint = build_document_fingerprint(document.text)
    cache_query = _build_cache_query(
        document_fingerprint=document_fingerprint,
        embedding_model=embedding_model,
        chunk_size_chars=chunk_size_chars,
        chunk_overlap_chars=chunk_overlap_chars,
        chunk_limit=chunk_limit,
    )

    cached_document = await collection.find_one(cache_query)
    if not cached_document:
        return None

    cached_chunks, cached_embeddings = _deserialize_cached_chunks(
        cached_document.get("chunks") or []
    )
    if not cached_embeddings or not _cached_chunks_match(chunks, cached_chunks):
        return None

    await collection.update_one(
        {"_id": cached_document["_id"]},
        {
            "$set": {"last_accessed_at": datetime.now(timezone.utc)},
            "$inc": {"access_count": 1},
        },
    )
    return cached_embeddings


async def upsert_document_embeddings(
    *,
    document: ExtractedDocument,
    chunks: list[TextChunk],
    chunk_embeddings: list[list[float]],
    embedding_model: str,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    chunk_limit: int,
) -> None:
    collection = get_document_rag_cache_collection()
    document_fingerprint = build_document_fingerprint(document.text)
    cache_query = _build_cache_query(
        document_fingerprint=document_fingerprint,
        embedding_model=embedding_model,
        chunk_size_chars=chunk_size_chars,
        chunk_overlap_chars=chunk_overlap_chars,
        chunk_limit=chunk_limit,
    )
    now = datetime.now(timezone.utc)
    serialized_chunks = [
        _serialize_chunk_payload(chunk=chunk, embedding=embedding)
        for chunk, embedding in zip(chunks, chunk_embeddings)
    ]

    await collection.update_one(
        cache_query,
        {
            "$set": {
                "document_title": document.title,
                "source_document_name": document.source_document_name,
                "source_document_type": document.source_document_type,
                "source_characters": document.source_characters,
                "chunks": serialized_chunks,
                "total_chunks": len(chunks),
                "updated_at": now,
                "last_accessed_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
            "$inc": {"access_count": 1},
        },
        upsert=True,
    )
