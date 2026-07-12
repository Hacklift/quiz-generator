from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.app.assistant.presentation_entities import PresentationEntity, PresentationEntityResolver
from server.app.assistant.schemas import ToolResult


@dataclass(frozen=True)
class ActionOutcome:
    step_id: str
    tool_name: str
    kind: str
    data: dict[str, Any]
    subject: PresentationEntity | None = None
    target: PresentationEntity | None = None
    recipient: str | None = None
    file_format: str | None = None
    count: int | None = None
    failed_count: int = 0
    internal: bool = False


INTERNAL_LOOKUP_TOOLS = {
    "library_find_saved_quiz_by_title",
    "library_get_history_detail",
    "library_get_saved_quiz",
    "folder_get",
    "folder_get_by_name",
}


def project_tool_outcomes(
    results: list[ToolResult],
    *,
    page_context: dict[str, Any] | None = None,
    recent_artifacts: list[dict[str, Any]] | None = None,
) -> list[ActionOutcome]:
    resolver = PresentationEntityResolver(
        results=results,
        page_context=page_context,
        recent_artifacts=recent_artifacts,
    )
    return [_project_result(result, resolver) for result in results if result.ok]


def _project_result(result: ToolResult, resolver: PresentationEntityResolver) -> ActionOutcome:
    data = result.data
    tool = result.tool_name
    subject: PresentationEntity | None = None
    target: PresentationEntity | None = None
    recipient: str | None = None
    file_format: str | None = None
    count: int | None = None
    failed_count = 0

    if tool in {
        "quiz_generate",
        "library_save_quiz",
        "share_create_link",
        "share_send_email",
        "live_quiz_get_access_link",
        "live_quiz_create_access_link",
        "live_quiz_ensure_access_link",
        "live_quiz_send_invites",
    }:
        subject = resolver.quiz(
            data.get("quiz_id"),
            title=data.get("title"),
            fallback="the quiz" if tool == "library_save_quiz" else "this quiz",
        )
    elif tool in {"quiz_get_answers", "quiz_export_link"}:
        subject = resolver.quiz(
            data.get("quiz_id"),
            title=data.get("display_title"),
            fallback=data.get("title") or "this quiz",
        )
    elif tool in {"saved_quiz_rename", "saved_quiz_delete"}:
        subject = resolver.saved_quiz(
            data.get("saved_quiz_id") or data.get("id"),
            quiz_id=data.get("quiz_id"),
            title=data.get("title"),
        )
    elif tool in {"folder_create", "folder_rename", "folder_delete"}:
        subject = resolver.folder(
            data.get("folder_id") or data.get("id"),
            name=data.get("name") or data.get("folder_name"),
        )
    elif tool == "folder_add_saved_quiz":
        subject = resolver.saved_quiz(
            data.get("saved_quiz_id"),
            quiz_id=data.get("quiz_id"),
            title=data.get("title"),
            fallback="the quiz",
        )
        target = resolver.folder(data.get("folder_id"), name=data.get("folder_name"), fallback="the folder")
    elif tool in {"folder_move_quiz", "folder_remove_quiz"}:
        subject = resolver.folder_item(data.get("folder_item_id") or data.get("id"), title=data.get("title"))
        target = resolver.folder(
            data.get("target_folder_id") or data.get("folder_id"),
            name=data.get("target_folder_name") or data.get("folder_name"),
            fallback="the folder",
        )

    if tool == "share_send_email":
        recipient = _optional_str(data.get("recipient_email"))
    elif tool == "quiz_export_link":
        file_format = str(data.get("format") or "file").upper()
    elif tool == "live_quiz_send_invites":
        count = int(data.get("sent_count") or 0)
        failed_count = int(data.get("failed_count") or 0)
        recipients = data.get("recipients")
        if count == 1 and isinstance(recipients, list) and recipients:
            recipient = _optional_str(recipients[0])

    return ActionOutcome(
        step_id=result.step_id,
        tool_name=tool,
        kind=tool.replace("_", "."),
        data=data,
        subject=subject,
        target=target,
        recipient=recipient,
        file_format=file_format,
        count=count,
        failed_count=failed_count,
        internal=tool in INTERNAL_LOOKUP_TOOLS,
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
