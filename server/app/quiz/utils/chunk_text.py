from __future__ import annotations

import re
from dataclasses import dataclass

from server.app.core.config import settings


_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass
class TextChunk:
    chunk_id: int
    content: str
    char_count: int


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    sentences = _SENTENCE_BOUNDARY_PATTERN.split(paragraph)
    if len(sentences) == 1:
        return [
            paragraph[index : index + max_chars]
            for index in range(0, len(paragraph), max_chars)
        ]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())
    return chunks


def split_text_into_chunks(
    text: str,
    *,
    max_chars: int | None = None,
    overlap_chars: int | None = None,
    max_chunks: int | None = None,
) -> list[TextChunk]:
    chunk_size = max_chars or settings.DOCUMENT_CHUNK_SIZE_CHARS
    overlap_size = overlap_chars or settings.DOCUMENT_CHUNK_OVERLAP_CHARS
    chunk_limit = max_chunks or settings.DOCUMENT_RAG_MAX_CHUNKS

    paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]
    prepared_segments: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            prepared_segments.append(paragraph)
        else:
            prepared_segments.extend(_split_long_paragraph(paragraph, chunk_size))

    chunks: list[TextChunk] = []
    current = ""

    for segment in prepared_segments:
        candidate = f"{current}\n\n{segment}".strip() if current else segment
        if current and len(candidate) > chunk_size:
            chunks.append(
                TextChunk(
                    chunk_id=len(chunks),
                    content=current.strip(),
                    char_count=len(current.strip()),
                )
            )
            overlap_prefix = current[-overlap_size:].strip() if overlap_size else ""
            current = f"{overlap_prefix}\n\n{segment}".strip() if overlap_prefix else segment
        else:
            current = candidate

        if len(chunks) >= chunk_limit:
            break

    if current.strip() and len(chunks) < chunk_limit:
        chunks.append(
            TextChunk(
                chunk_id=len(chunks),
                content=current.strip(),
                char_count=len(current.strip()),
            )
        )

    return chunks
