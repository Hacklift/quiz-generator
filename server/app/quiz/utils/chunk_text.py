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


def _join_segments(segments: list[str]) -> str:
    return "\n\n".join(segment.strip() for segment in segments if segment.strip()).strip()


def _select_overlap_segments(segments: list[str], overlap_size: int) -> list[str]:
    if overlap_size <= 0:
        return []

    overlap_segments: list[str] = []
    total_length = 0

    for segment in reversed(segments):
        segment = segment.strip()
        if not segment:
            continue

        separator_length = 2 if overlap_segments else 0
        projected_length = total_length + separator_length + len(segment)

        if overlap_segments and projected_length > overlap_size:
            break

        overlap_segments.append(segment)
        total_length = projected_length

        if total_length >= overlap_size:
            break

    return list(reversed(overlap_segments))


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
    current_segments: list[str] = []

    for segment in prepared_segments:
        candidate_segments = [*current_segments, segment]
        candidate = _join_segments(candidate_segments)

        if current_segments and len(candidate) > chunk_size:
            current_content = _join_segments(current_segments)
            chunks.append(
                TextChunk(
                    chunk_id=len(chunks),
                    content=current_content,
                    char_count=len(current_content),
                )
            )

            overlap_segments = _select_overlap_segments(current_segments, overlap_size)
            current_segments = [*overlap_segments, segment]

            while len(_join_segments(current_segments)) > chunk_size and len(current_segments) > 1:
                current_segments = current_segments[1:]
        else:
            current_segments = candidate_segments

        if len(chunks) >= chunk_limit:
            break

    current_content = _join_segments(current_segments)
    if current_content and len(chunks) < chunk_limit:
        chunks.append(
            TextChunk(
                chunk_id=len(chunks),
                content=current_content,
                char_count=len(current_content),
            )
        )

    return chunks
