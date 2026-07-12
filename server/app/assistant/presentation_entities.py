from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.app.assistant.schemas import ToolResult


@dataclass(frozen=True)
class PresentationEntity:
    resource_type: str
    canonical_id: str | None
    title: str

    @property
    def correlation_key(self) -> tuple[str, str] | None:
        if not self.canonical_id:
            return None
        return self.resource_type, self.canonical_id


class PresentationEntityResolver:
    def __init__(
        self,
        *,
        results: list[ToolResult],
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ):
        self.sources: list[Any] = [
            *(result.data for result in reversed(results)),
            page_context or {},
            *(reversed(recent_artifacts or [])),
        ]

    def quiz(self, quiz_id: Any, *, title: Any = None, fallback: str = "this quiz") -> PresentationEntity:
        canonical_id = _optional_str(quiz_id)
        resolved_title = (
            self._find_title(
                canonical_id,
                id_keys=("quiz_id", "canonical_quiz_id", "current_quiz_id", "id"),
                title_keys=("display_title",),
            )
            or _optional_str(title)
            or self._find_title(
                canonical_id,
                id_keys=("quiz_id", "canonical_quiz_id", "current_quiz_id", "id"),
            )
        )
        return PresentationEntity("quiz", canonical_id, resolved_title or fallback)

    def saved_quiz(
        self,
        saved_quiz_id: Any,
        *,
        quiz_id: Any = None,
        title: Any = None,
        fallback: str = "this saved quiz",
    ) -> PresentationEntity:
        saved_id = _optional_str(saved_quiz_id)
        canonical_quiz_id = _optional_str(quiz_id)
        resolved_title = (
            _optional_str(title)
            or self._find_title(saved_id, id_keys=("saved_quiz_id", "id"))
            or self._find_title(
                canonical_quiz_id,
                id_keys=("quiz_id", "canonical_quiz_id", "current_quiz_id", "id"),
            )
        )
        return PresentationEntity("quiz", canonical_quiz_id or saved_id, resolved_title or fallback)

    def folder(self, folder_id: Any, *, name: Any = None, fallback: str = "this folder") -> PresentationEntity:
        canonical_id = _optional_str(folder_id)
        resolved_name = _optional_str(name) or self._find_title(
            canonical_id,
            id_keys=("folder_id", "id"),
            title_keys=("name", "folder_name", "label"),
        )
        return PresentationEntity("folder", canonical_id, resolved_name or fallback)

    def folder_item(self, folder_item_id: Any, *, title: Any = None) -> PresentationEntity:
        canonical_id = _optional_str(folder_item_id)
        resolved_title = _optional_str(title) or self._find_title(
            canonical_id,
            id_keys=("folder_item_id", "id"),
        )
        quiz_id = self._find_value(canonical_id, id_keys=("folder_item_id", "id"), value_key="quiz_id")
        return PresentationEntity("quiz", _optional_str(quiz_id) or canonical_id, resolved_title or "this quiz")

    def _find_title(
        self,
        target_id: str | None,
        *,
        id_keys: tuple[str, ...],
        title_keys: tuple[str, ...] = ("display_title", "title", "quiz_title", "quiz_name", "name", "label"),
    ) -> str | None:
        if not target_id:
            return None
        for source in self.sources:
            value = _find_mapping_value(source, target_id, id_keys=id_keys, value_keys=title_keys)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _find_value(self, target_id: str | None, *, id_keys: tuple[str, ...], value_key: str) -> Any:
        if not target_id:
            return None
        for source in self.sources:
            value = _find_mapping_value(source, target_id, id_keys=id_keys, value_keys=(value_key,))
            if value is not None:
                return value
        return None


def _find_mapping_value(
    value: Any,
    target_id: str,
    *,
    id_keys: tuple[str, ...],
    value_keys: tuple[str, ...],
) -> Any:
    if isinstance(value, dict):
        metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
        ids = {str(value.get(key) or "") for key in id_keys}
        ids.update(str(metadata.get(key) or "") for key in id_keys)
        if target_id in ids:
            summary = value.get("quiz_summary") if isinstance(value.get("quiz_summary"), dict) else {}
            for source in (value, metadata, summary):
                for key in value_keys:
                    candidate = source.get(key)
                    if candidate is not None:
                        return candidate
        for child in value.values():
            candidate = _find_mapping_value(child, target_id, id_keys=id_keys, value_keys=value_keys)
            if candidate is not None:
                return candidate
    elif isinstance(value, list):
        for item in value:
            candidate = _find_mapping_value(item, target_id, id_keys=id_keys, value_keys=value_keys)
            if candidate is not None:
                return candidate
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
