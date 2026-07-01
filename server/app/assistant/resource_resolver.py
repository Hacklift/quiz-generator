from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz


QUIZ_RESOURCES = {
    "quiz",
    "quiz_history",
    "saved_quiz",
    "folder_quiz",
    "folder_quiz_match",
}


@dataclass(frozen=True)
class ResolvedQuizResource:
    resource: str
    title: str
    quiz_id: str | None = None
    question_type: str | None = None
    saved_quiz_id: str | None = None
    history_id: str | None = None
    folder_item_id: str | None = None
    href: str | None = None
    score: int = 0


class AssistantResourceResolver:
    def resolve_quiz(
        self,
        *,
        message: str,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> ResolvedQuizResource | None:
        candidates = self._quiz_candidates(page_context=page_context, recent_artifacts=recent_artifacts)
        if not candidates:
            return None

        direct_context = self._direct_context_quiz(page_context)
        if direct_context and self._message_refers_to_current_quiz(message):
            return direct_context

        scored = [
            self._score_candidate(candidate, message)
            for candidate in candidates
        ]
        scored = [candidate for candidate in scored if candidate.score >= 72]
        if not scored:
            if self._message_refers_to_current_quiz(message):
                return direct_context or candidates[0]
            return None
        return max(scored, key=lambda candidate: candidate.score)

    def _quiz_candidates(
        self,
        *,
        page_context: dict[str, Any] | None,
        recent_artifacts: list[dict[str, Any]] | None,
    ) -> list[ResolvedQuizResource]:
        candidates: list[ResolvedQuizResource] = []
        direct = self._direct_context_quiz(page_context)
        if direct is not None:
            candidates.append(direct)

        for artifact in recent_artifacts or []:
            if not isinstance(artifact, dict):
                continue
            data = artifact.get("data")
            if not isinstance(data, dict):
                continue
            resource = str(data.get("resource") or "")
            if resource not in QUIZ_RESOURCES:
                continue

            if artifact.get("type") == "resource_list":
                items = data.get("items")
                if isinstance(items, list):
                    for item in items:
                        candidate = self._candidate_from_item(resource=resource, item=item)
                        if candidate is not None:
                            candidates.append(candidate)
                continue

            candidate = self._candidate_from_item(
                resource=resource,
                item={
                    "id": data.get("id"),
                    "label": data.get("label"),
                    "href": data.get("href"),
                    "metadata": data.get("metadata"),
                },
            )
            if candidate is not None:
                candidates.append(candidate)

        return self._dedupe_candidates(candidates)

    def _direct_context_quiz(self, page_context: dict[str, Any] | None) -> ResolvedQuizResource | None:
        if not isinstance(page_context, dict):
            return None
        quiz_id = page_context.get("current_quiz_id")
        summary = page_context.get("quiz_summary") if isinstance(page_context.get("quiz_summary"), dict) else {}
        title = summary.get("title") or summary.get("quiz_title") or page_context.get("title")
        if not quiz_id and not title:
            return None
        return ResolvedQuizResource(
            resource="quiz",
            title=str(title or "current quiz"),
            quiz_id=str(quiz_id) if quiz_id else None,
            question_type=summary.get("question_type") or summary.get("quiz_type"),
            score=100,
        )

    def _candidate_from_item(self, *, resource: str, item: Any) -> ResolvedQuizResource | None:
        if not isinstance(item, dict):
            return None
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        title = (
            item.get("label")
            or item.get("title")
            or metadata.get("title")
            or metadata.get("quiz_name")
            or metadata.get("label")
        )
        if not title:
            return None

        item_id = item.get("id") or metadata.get("id") or metadata.get("_id")
        return ResolvedQuizResource(
            resource=resource,
            title=str(title),
            quiz_id=_optional_str(item.get("quiz_id") or metadata.get("quiz_id") or metadata.get("canonical_quiz_id")),
            question_type=_optional_str(item.get("question_type") or metadata.get("question_type") or metadata.get("quiz_type")),
            saved_quiz_id=_optional_str(item.get("saved_quiz_id") or metadata.get("saved_quiz_id") or (item_id if resource == "saved_quiz" else None)),
            history_id=_optional_str(item.get("history_id") or metadata.get("history_id") or (item_id if resource == "quiz_history" else None)),
            folder_item_id=_optional_str(item.get("folder_item_id") or metadata.get("folder_item_id") or (item_id if resource.startswith("folder_quiz") else None)),
            href=_optional_str(item.get("href")),
        )

    def _score_candidate(self, candidate: ResolvedQuizResource, message: str) -> ResolvedQuizResource:
        message_text = message.casefold()
        title_text = candidate.title.casefold()
        if title_text and title_text in message_text:
            score = 100
        else:
            score = max(
                fuzz.partial_ratio(title_text, message_text),
                fuzz.token_set_ratio(title_text, message_text),
            )
        return ResolvedQuizResource(
            resource=candidate.resource,
            title=candidate.title,
            quiz_id=candidate.quiz_id,
            question_type=candidate.question_type,
            saved_quiz_id=candidate.saved_quiz_id,
            history_id=candidate.history_id,
            folder_item_id=candidate.folder_item_id,
            href=candidate.href,
            score=int(score),
        )

    def _dedupe_candidates(self, candidates: list[ResolvedQuizResource]) -> list[ResolvedQuizResource]:
        seen: set[tuple[str | None, str | None, str]] = set()
        deduped: list[ResolvedQuizResource] = []
        for candidate in candidates:
            key = (candidate.quiz_id, candidate.saved_quiz_id, candidate.title.casefold())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped

    def _message_refers_to_current_quiz(self, message: str) -> bool:
        normalized = message.casefold()
        return any(
            phrase in normalized
            for phrase in (
                "this quiz",
                "that quiz",
                "the quiz",
                "it",
                "above",
                "generated above",
                "pulled up above",
                "just pulled",
                "last quiz",
            )
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None
