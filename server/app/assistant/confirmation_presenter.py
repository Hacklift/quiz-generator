from __future__ import annotations

from typing import Any

from server.app.assistant.presentation_entities import PresentationEntityResolver
from server.app.assistant.schemas import ToolResult


class ConfirmationPresenter:
    def label(self, tool_name: str) -> str:
        return {
            "share_create_link": "Create share link",
            "share_send_email": "Send quiz email",
            "live_quiz_create_access_link": "Create live quiz link",
            "live_quiz_send_invites": "Send live quiz invites",
            "library_save_quiz": "Save quiz",
            "saved_quiz_rename": "Rename saved quiz",
            "saved_quiz_delete": "Delete saved quiz",
            "folder_create": "Create folder",
            "folder_add_saved_quiz": "Add quiz to folder",
            "folder_rename": "Rename folder",
            "folder_delete": "Delete folder",
            "folder_remove_quiz": "Remove quiz from folder",
            "folder_move_quiz": "Move quiz",
            "notification_delete": "Delete notification",
        }.get(tool_name, "Confirm action")

    def message(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        results: list[ToolResult],
        page_context: dict[str, Any] | None,
        recent_artifacts: list[dict[str, Any]] | None,
    ) -> str:
        resolver = PresentationEntityResolver(
            results=results,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        if tool_name == "folder_move_quiz":
            quiz = resolver.folder_item(arguments.get("folder_item_id"))
            source = resolver.folder(arguments.get("source_folder_id"))
            target = resolver.folder(arguments.get("target_folder_id"))
            return f"Please confirm: move {quiz.title} from {source.title} to {target.title}."
        if tool_name == "folder_delete":
            folder = resolver.folder(arguments.get("folder_id"))
            return f"Please confirm: delete {folder.title} folder."
        if tool_name == "folder_remove_quiz":
            quiz = resolver.folder_item(arguments.get("folder_item_id"))
            folder = resolver.folder(arguments.get("folder_id"))
            return f"Please confirm: remove {quiz.title} from {folder.title}."
        if tool_name == "folder_add_saved_quiz":
            folder = resolver.folder(arguments.get("folder_id"))
            quiz = resolver.saved_quiz(arguments.get("saved_quiz_id"))
            return f"Please confirm: add {quiz.title} to {folder.title}."
        if tool_name == "folder_create":
            return f"Please confirm: create the {arguments.get('name') or 'this folder'} folder."
        if tool_name == "folder_rename":
            return f"Please confirm: rename this folder to {arguments.get('new_name') or 'the new name'}."
        if tool_name == "library_save_quiz":
            quiz = resolver.quiz(arguments.get("quiz_id"), title=arguments.get("title"))
            return f"Please confirm: save {quiz.title} to your library."
        if tool_name == "saved_quiz_rename":
            current = resolver.saved_quiz(arguments.get("saved_quiz_id"))
            return f"Please confirm: rename {current.title} to {arguments.get('title') or 'the new title'}."
        if tool_name == "saved_quiz_delete":
            return "Please confirm: delete this saved quiz."
        if tool_name == "share_create_link":
            quiz = resolver.quiz(arguments.get("quiz_id"))
            return f"Please confirm: create a share link for {quiz.title}."
        if tool_name == "share_send_email":
            quiz = resolver.quiz(arguments.get("quiz_id"))
            link_name = f"{quiz.title} link" if quiz.title.casefold().endswith("quiz") else f"{quiz.title} quiz link"
            article = "" if quiz.title.casefold().startswith(("this ", "that ", "the ")) else "the "
            return f"Please confirm: send {article}{link_name} to {arguments.get('recipient_email') or 'the recipient'}."
        if tool_name == "live_quiz_create_access_link":
            quiz = resolver.quiz(arguments.get("quiz_id"))
            return f"Please confirm: create a live quiz link for {quiz.title}."
        if tool_name == "live_quiz_send_invites":
            recipients = arguments.get("recipient_emails")
            quiz = resolver.quiz(arguments.get("quiz_id"))
            if isinstance(recipients, list):
                if len(recipients) == 1:
                    return f"Please confirm: send {quiz.title} quiz invite to {recipients[0]}."
                return f"Please confirm: send {quiz.title} quiz invites to {len(recipients)} recipients."
            return f"Please confirm: send {quiz.title} quiz invites."
        if tool_name == "notification_delete":
            return "Please confirm: delete this notification."
        return "Please confirm this action."


def find_title_for_id(value: Any, target_id: str, *, id_keys: tuple[str, ...]) -> str | None:
    if isinstance(value, dict):
        metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
        ids = {str(value.get(key) or "") for key in id_keys}
        ids.update(str(metadata.get(key) or "") for key in id_keys)
        if target_id in ids:
            summary = value.get("quiz_summary") if isinstance(value.get("quiz_summary"), dict) else {}
            for source in (value, metadata, summary):
                for key in ("title", "quiz_title", "name", "label"):
                    candidate = source.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip()
        for child in value.values():
            title = find_title_for_id(child, target_id, id_keys=id_keys)
            if title:
                return title
    elif isinstance(value, list):
        for item in value:
            title = find_title_for_id(item, target_id, id_keys=id_keys)
            if title:
                return title
    return None
