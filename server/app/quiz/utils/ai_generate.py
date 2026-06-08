from __future__ import annotations

import asyncio
import functools
import json
import math
import os
from dataclasses import dataclass
from typing import Any, Optional

from huggingface_hub import InferenceClient
from huggingface_hub.inference._providers import get_provider_helper

from server.app.core.config import settings
from server.app.quiz.repositories.document_rag_repository import (
    get_cached_document_embeddings,
    upsert_document_embeddings,
)
from server.app.quiz.repositories.token_repository import get_user_token
from server.app.quiz.utils.chunk_text import TextChunk
from server.app.quiz.utils.extract_text import ExtractedDocument


@dataclass
class RetrievedChunk:
    chunk: TextChunk
    score: float


@dataclass
class DocumentQuizGenerationResult:
    title: str
    description: str
    retrieval_query: str
    retrieved_chunks: list[RetrievedChunk]
    questions: list[dict[str, Any]]
    rag_strategy: str
    embedding_cache_hit: bool


async def resolve_document_quiz_token(
    user_id: Optional[str],
    provided_token: Optional[str],
) -> Optional[str]:
    if provided_token:
        return provided_token

    if user_id:
        saved = await get_user_token(user_id)
        if saved:
            return saved

    return os.getenv("HUGGINGFACEHUB_API_TOKEN")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0

    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _mean_embedding(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dimensions = len(vectors[0])
    return [
        sum(vector[index] for vector in vectors) / len(vectors)
        for index in range(dimensions)
    ]


def _normalize_embedding(values: list[float]) -> list[float]:
    if not values:
        return []
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _coerce_embedding_vector(payload: Any) -> list[float]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Embedding response was empty or had an unexpected format.")

    if all(isinstance(item, (int, float)) for item in payload):
        return [float(item) for item in payload]

    nested_vectors: list[list[float]] = []
    for item in payload:
        if isinstance(item, list) and item and all(
            isinstance(value, (int, float)) for value in item
        ):
            nested_vectors.append([float(value) for value in item])

    if not nested_vectors:
        raise ValueError("Embedding response could not be converted into a vector.")

    return _mean_embedding(nested_vectors)


def _normalize_question_type(question_type: str) -> str:
    normalized = question_type.strip().lower()
    aliases = {
        "multiple-choice": "multichoice",
        "multiple choice": "multichoice",
        "multiple_choice": "multichoice",
        "true_false": "true-false",
        "true/false": "true-false",
        "open ended": "open-ended",
        "open_ended": "open-ended",
        "short answer": "short-answer",
        "short_answer": "short-answer",
    }
    return aliases.get(normalized, normalized)


async def _feature_extract_text(
    client: InferenceClient,
    text: str,
    *,
    model: str,
) -> list[float]:
    loop = asyncio.get_event_loop()

    provider_helper = get_provider_helper(
        getattr(client, "provider", "hf-inference"),
        task="feature-extraction",
        model=model,
    )
    request_parameters = provider_helper.prepare_request(
        inputs=text,
        parameters={"normalize": False},
        headers=client.headers,
        model=model,
        api_key=client.token,
    )

    response = await loop.run_in_executor(
        None,
        functools.partial(
            client._inner_post,
            request_parameters,
        ),
    )
    embedding_payload = provider_helper.get_response(response, request_parameters)
    return _normalize_embedding(_coerce_embedding_vector(embedding_payload))


def _build_retrieval_query(
    *,
    document: ExtractedDocument,
    question_type: str,
    difficulty_level: str,
    audience_type: str,
    custom_instruction: str | None,
    focus_topic: str | None,
) -> str:
    focus = focus_topic.strip() if focus_topic else ""
    instruction = custom_instruction.strip() if custom_instruction else ""
    parts = [
        document.title,
        focus,
        f"{difficulty_level} {question_type} quiz",
        f"for {audience_type}",
        "key definitions, facts, explanations, and examples",
        instruction,
    ]
    return " ".join(part for part in parts if part).strip()


def _select_relevant_chunks(
    chunks: list[TextChunk],
    chunk_embeddings: list[list[float]],
    query_embedding: list[float],
    *,
    top_k: int,
) -> list[RetrievedChunk]:
    centroid = _mean_embedding(chunk_embeddings)
    scored_candidates: list[tuple[int, float, float, float]] = []

    for index, chunk_embedding in enumerate(chunk_embeddings):
        query_score = _cosine_similarity(query_embedding, chunk_embedding)
        centroid_score = _cosine_similarity(centroid, chunk_embedding)
        hybrid_score = (0.7 * query_score) + (0.3 * centroid_score)
        scored_candidates.append((index, hybrid_score, query_score, centroid_score))

    ranked = sorted(scored_candidates, key=lambda item: item[1], reverse=True)
    pool = ranked[: max(top_k * 3, top_k)]
    selected_indices: list[int] = []

    for index, hybrid_score, _, _ in pool:
        if len(selected_indices) >= top_k:
            break
        if not selected_indices:
            selected_indices.append(index)
            continue

        diversity_penalty = max(
            _cosine_similarity(chunk_embeddings[index], chunk_embeddings[selected])
            for selected in selected_indices
        )
        mmr_score = (0.7 * hybrid_score) - (0.3 * diversity_penalty)
        if mmr_score > -1:
            selected_indices.append(index)

    if len(selected_indices) < min(top_k, len(chunks)):
        for index, _, _, _ in ranked:
            if index not in selected_indices:
                selected_indices.append(index)
            if len(selected_indices) >= min(top_k, len(chunks)):
                break

    selected = sorted(
        (
            RetrievedChunk(
                chunk=chunks[index],
                score=next(score for idx, score, _, _ in scored_candidates if idx == index),
            )
            for index in selected_indices
        ),
        key=lambda item: item.chunk.chunk_id,
    )
    return selected


def _build_generation_prompt(
    *,
    document: ExtractedDocument,
    retrieved_chunks: list[RetrievedChunk],
    question_type: str,
    num_questions: int,
    difficulty_level: str,
    audience_type: str,
    custom_instruction: str | None,
) -> str:
    question_type = _normalize_question_type(question_type)
    options_rule = (
        "Each question must have exactly four options and one correct answer."
        if question_type == "multichoice"
        else "Use options only when the question type needs them."
    )
    custom_part = (
        f"Additional instructor guidance: {custom_instruction.strip()}"
        if custom_instruction and custom_instruction.strip()
        else ""
    )
    chunk_text = "\n\n".join(
        f"[Chunk {item.chunk.chunk_id}] {item.chunk.content}"
        for item in retrieved_chunks
    )

    return f"""
You are generating a quiz strictly from retrieved learning material excerpts.

Rules:
- Use ONLY the provided chunks.
- Do NOT use outside knowledge.
- If the chunks do not support a question, do not invent one.
- Keep the quiz at {difficulty_level} difficulty for {audience_type} learners.
- Generate exactly {num_questions} {question_type} questions.
- {options_rule}
- Return ONLY valid JSON.

JSON format:
{{
  "title": "{document.title}",
  "questions": [
    {{
      "question": "string",
      "options": ["string", "string", "string", "string"] or null,
      "answer": "string",
      "explanation": "string",
      "question_type": "{question_type}"
    }}
  ]
}}

{custom_part}

Retrieved chunks:
{chunk_text}
""".strip()


async def _resolve_chunk_embeddings(
    *,
    client: InferenceClient,
    document: ExtractedDocument,
    chunks: list[TextChunk],
) -> tuple[list[list[float]], bool]:
    if settings.DOCUMENT_RAG_CACHE_ENABLED:
        cached_embeddings = await get_cached_document_embeddings(
            document=document,
            chunks=chunks,
            embedding_model=settings.HF_EMBEDDING_MODEL,
            chunk_size_chars=settings.DOCUMENT_CHUNK_SIZE_CHARS,
            chunk_overlap_chars=settings.DOCUMENT_CHUNK_OVERLAP_CHARS,
            chunk_limit=settings.DOCUMENT_RAG_MAX_CHUNKS,
        )
        if cached_embeddings:
            return cached_embeddings, True

    chunk_embeddings: list[list[float]] = []
    for chunk in chunks:
        chunk_embeddings.append(
            await _feature_extract_text(
                client,
                chunk.content,
                model=settings.HF_EMBEDDING_MODEL,
            )
        )

    if settings.DOCUMENT_RAG_CACHE_ENABLED:
        await upsert_document_embeddings(
            document=document,
            chunks=chunks,
            chunk_embeddings=chunk_embeddings,
            embedding_model=settings.HF_EMBEDDING_MODEL,
            chunk_size_chars=settings.DOCUMENT_CHUNK_SIZE_CHARS,
            chunk_overlap_chars=settings.DOCUMENT_CHUNK_OVERLAP_CHARS,
            chunk_limit=settings.DOCUMENT_RAG_MAX_CHUNKS,
        )

    return chunk_embeddings, False


def _extract_first_json_object(raw_text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw_text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw_text[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError("Model response did not contain a valid JSON object.")


def _normalize_multichoice_answer(answer: str, options: list[str]) -> str:
    normalized_answer = str(answer).strip()
    if normalized_answer in options:
        return normalized_answer

    if len(normalized_answer) == 1 and normalized_answer.upper() in {"A", "B", "C", "D"}:
        option_index = ord(normalized_answer.upper()) - ord("A")
        if 0 <= option_index < len(options):
            return options[option_index]

    for option in options:
        cleaned_option = option.split(")", 1)[-1].strip() if ")" in option else option.strip()
        if cleaned_option.lower() == normalized_answer.lower():
            return option
    return normalized_answer


def _normalize_generated_questions(
    payload: dict[str, Any],
    *,
    question_type: str,
    num_questions: int,
) -> list[dict[str, Any]]:
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("Model response is missing the questions array.")

    normalized_questions: list[dict[str, Any]] = []
    normalized_type = _normalize_question_type(question_type)

    for raw_question in raw_questions:
        if not isinstance(raw_question, dict):
            continue

        question = str(raw_question.get("question", "")).strip()
        answer = str(raw_question.get("answer", "")).strip()
        explanation = str(raw_question.get("explanation", "")).strip() or None
        options = raw_question.get("options")

        if not question or not answer:
            continue

        if normalized_type == "multichoice":
            if not isinstance(options, list) or len(options) != 4:
                continue
            normalized_options = [str(option).strip() for option in options]
            if not all(normalized_options):
                continue
            answer = _normalize_multichoice_answer(answer, normalized_options)
            normalized_questions.append(
                {
                    "question": question,
                    "options": normalized_options,
                    "answer": answer,
                    "explanation": explanation,
                    "question_type": normalized_type,
                }
            )
        elif normalized_type == "true-false":
            normalized_questions.append(
                {
                    "question": question,
                    "options": ["True", "False"],
                    "answer": "True" if answer.lower() == "true" else "False",
                    "explanation": explanation,
                    "question_type": normalized_type,
                }
            )
        else:
            normalized_questions.append(
                {
                    "question": question,
                    "options": None,
                    "answer": answer,
                    "explanation": explanation,
                    "question_type": normalized_type,
                }
            )

    if len(normalized_questions) < num_questions:
        raise ValueError(
            f"The model returned {len(normalized_questions)} valid questions; {num_questions} were requested."
        )

    return normalized_questions[:num_questions]


async def generate_document_quiz_with_rag(
    *,
    document: ExtractedDocument,
    chunks: list[TextChunk],
    question_type: str,
    num_questions: int,
    difficulty_level: str,
    audience_type: str,
    custom_instruction: str | None,
    focus_topic: str | None,
    user_id: str | None,
    token: str | None,
) -> DocumentQuizGenerationResult:
    final_token = await resolve_document_quiz_token(user_id, token)
    if not final_token:
        raise ValueError("A Hugging Face token is required for document quiz generation.")

    client = InferenceClient(token=final_token)
    retrieval_query = _build_retrieval_query(
        document=document,
        question_type=question_type,
        difficulty_level=difficulty_level,
        audience_type=audience_type,
        custom_instruction=custom_instruction,
        focus_topic=focus_topic,
    )

    chunk_embeddings, embedding_cache_hit = await _resolve_chunk_embeddings(
        client=client,
        document=document,
        chunks=chunks,
    )

    query_embedding = await _feature_extract_text(
        client,
        retrieval_query,
        model=settings.HF_EMBEDDING_MODEL,
    )
    retrieved_chunks = _select_relevant_chunks(
        chunks,
        chunk_embeddings,
        query_embedding,
        top_k=min(settings.DOCUMENT_RAG_TOP_K, len(chunks)),
    )

    generation_prompt = _build_generation_prompt(
        document=document,
        retrieved_chunks=retrieved_chunks,
        question_type=question_type,
        num_questions=num_questions,
        difficulty_level=difficulty_level,
        audience_type=audience_type,
        custom_instruction=custom_instruction,
    )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        functools.partial(
            client.chat_completion,
            model=settings.HF_QUIZ_MODEL,
            messages=[{"role": "user", "content": generation_prompt}],
            max_tokens=2400,
            temperature=0.3,
        ),
    )
    response_text = response.choices[0].message.content
    payload = _extract_first_json_object(response_text)
    questions = _normalize_generated_questions(
        payload,
        question_type=question_type,
        num_questions=num_questions,
    )

    return DocumentQuizGenerationResult(
        title=document.title,
        description=(
            f"Generated from {document.source_document_type.upper()} material "
            f"using {len(retrieved_chunks)} retrieved chunks."
        ),
        retrieval_query=retrieval_query,
        retrieved_chunks=retrieved_chunks,
        questions=questions,
        rag_strategy="persistent_embedding_mmr",
        embedding_cache_hit=embedding_cache_hit,
    )
