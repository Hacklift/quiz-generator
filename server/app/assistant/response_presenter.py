from __future__ import annotations

from typing import Any

from server.app.assistant.outcomes import ActionOutcome, project_tool_outcomes
from server.app.assistant.schemas import AssistantFinalResponse, ToolResult


class AssistantResponsePresenter:
    """Build complete responses from semantic outcomes, not tool combinations."""

    def present(
        self,
        results: list[ToolResult],
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> AssistantFinalResponse | None:
        outcomes = project_tool_outcomes(
            results,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        phrases = _OutcomeSentenceComposer().compose(outcomes)
        if not phrases:
            return self._present_read_result(results[-1]) if results else None

        message = f"I {_join_phrases(phrases)}."
        export = next((item for item in reversed(outcomes) if item.tool_name == "quiz_export_link"), None)
        if export is not None:
            message = f"{message} {_download_instruction(export)}"
        answer = next((item for item in outcomes if item.tool_name == "quiz_get_answers"), None)
        if answer and answer.data.get("model_warning"):
            message = f"{message} {answer.data['model_warning']}"
        return AssistantFinalResponse(message=message)

    def _present_read_result(self, result: ToolResult) -> AssistantFinalResponse | None:
        data = result.data
        if result.tool_name == "library_list_saved_quizzes":
            count = _item_count(data)
            return AssistantFinalResponse(message=f"You have {count} saved {'quiz' if count == 1 else 'quizzes'}.")
        if result.tool_name == "library_list_history":
            count = _item_count(data)
            return AssistantFinalResponse(message=f"I found {count} quiz history item{'s' if count != 1 else ''}.")
        if result.tool_name == "folder_list":
            count = _item_count(data)
            return AssistantFinalResponse(message=f"I found {count} folder{'s' if count != 1 else ''}.")
        if result.tool_name == "folder_get_by_name":
            name = data.get("name") or "that folder"
            if data.get("found") is False:
                return AssistantFinalResponse(message=f"You do not have a folder named {name}.")
            quizzes = data.get("quizzes")
            count = len(quizzes) if isinstance(quizzes, list) else 0
            return AssistantFinalResponse(message=f"I found {count} {'quiz' if count == 1 else 'quizzes'} in {name} Folder.")
        if result.tool_name == "folder_find_quiz_by_title":
            return _folder_match_response(data)
        if result.tool_name == "notification_list":
            items = data.get("items") if isinstance(data, dict) else []
            count = len(items) if isinstance(items, list) else 0
            unread = data.get("unread_count") if isinstance(data, dict) else None
            suffix = f"; {unread} unread" if isinstance(unread, int) else ""
            return AssistantFinalResponse(message=f"I found {count} notification{'s' if count != 1 else ''}{suffix}.")
        return None


class _OutcomeSentenceComposer:
    def __init__(self):
        self.mentioned: set[tuple[str, str]] = set()
        self.share_links: set[tuple[str, str]] = set()
        self.live_links: set[tuple[str, str]] = set()

    def compose(self, outcomes: list[ActionOutcome]) -> list[str]:
        phrases: list[str] = []
        for outcome in outcomes:
            if outcome.internal:
                continue
            phrase = self._phrase(outcome)
            if phrase:
                phrases.append(phrase)
        return phrases

    def _phrase(self, outcome: ActionOutcome) -> str | None:
        tool = outcome.tool_name
        subject = outcome.subject
        if tool == "quiz_generate":
            return f"generated {self._reference(subject, allow_pronoun=False)}"
        if tool == "quiz_get_answers":
            count = outcome.data.get("answer_count") or 0
            return f"found {count} answer{'s' if count != 1 else ''} for {self._reference(subject)}"
        if tool == "library_save_quiz":
            return f"saved {self._reference(subject)}"
        if tool == "saved_quiz_rename":
            return f"renamed the saved quiz to {self._reference(subject, allow_pronoun=False)}"
        if tool == "saved_quiz_delete":
            return f"deleted {self._reference(subject)}"
        if tool == "folder_create":
            return f"created {self._reference(subject, allow_pronoun=False)}"
        if tool == "folder_rename":
            return f"renamed the folder to {self._reference(subject, allow_pronoun=False)}"
        if tool == "folder_delete":
            return f"deleted {self._reference(subject)} folder"
        if tool == "folder_add_saved_quiz":
            return f"added {self._reference(subject)} to {self._reference(outcome.target, allow_pronoun=False)}"
        if tool == "folder_remove_quiz":
            return f"removed {self._reference(subject)} from {self._reference(outcome.target, allow_pronoun=False)}"
        if tool == "folder_move_quiz":
            return f"moved {self._reference(subject)} to {self._reference(outcome.target, allow_pronoun=False)}"
        if tool == "share_create_link":
            self._remember_link(self.share_links, subject)
            return f"created a share link for {self._reference(subject)}"
        if tool == "share_send_email":
            recipient = outcome.recipient or "the recipient"
            if self._has_link(self.share_links, subject):
                self._remember(subject)
                return f"sent it to {recipient}"
            title = self._reference(subject, allow_pronoun=False)
            link_name = f"{title} link" if title.casefold().endswith("quiz") else f"{title} quiz link"
            article = "" if title.casefold().startswith(("this ", "that ", "the ")) else "the "
            return f"sent {article}{link_name} to {recipient}"
        if tool == "quiz_export_link":
            self._remember(subject)
            return f"prepared the {outcome.file_format or 'file'} download"
        if tool == "live_quiz_get_access_link":
            if outcome.data.get("found") is False:
                return f"found no active live quiz link for {self._reference(subject)}"
            self._remember_link(self.live_links, subject)
            return f"found an active live quiz link for {self._reference(subject)}"
        if tool in {"live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
            self._remember_link(self.live_links, subject)
            action = "reused the active live quiz link" if outcome.data.get("reused_existing") else "created a live quiz link"
            return f"{action} for {self._reference(subject)}"
        if tool == "live_quiz_send_invites":
            count = outcome.count or 0
            if outcome.recipient:
                phrase = f"sent it to {outcome.recipient}" if self._has_link(self.live_links, subject) else f"sent a live quiz invite to {outcome.recipient}"
            else:
                phrase = f"sent live quiz invite{'s' if count != 1 else ''} to {count} recipient{'s' if count != 1 else ''}"
            return f"{phrase}; {outcome.failed_count} failed" if outcome.failed_count else phrase
        if tool == "notification_mark_read":
            return "marked the notification as read"
        if tool == "notification_delete":
            return "deleted the notification"
        return None

    def _reference(self, entity, *, allow_pronoun: bool = True) -> str:
        if entity is None:
            return "it" if allow_pronoun else "the item"
        key = entity.correlation_key
        if allow_pronoun and key and key in self.mentioned:
            return "it"
        self._remember(entity)
        return entity.title

    def _remember(self, entity) -> None:
        if entity and entity.correlation_key:
            self.mentioned.add(entity.correlation_key)

    def _remember_link(self, collection: set[tuple[str, str]], entity) -> None:
        if entity and entity.correlation_key:
            collection.add(entity.correlation_key)

    @staticmethod
    def _has_link(collection: set[tuple[str, str]], entity) -> bool:
        return bool(entity and entity.correlation_key and entity.correlation_key in collection)


def outcome_artifact_label(outcome: ActionOutcome) -> str | None:
    subject = outcome.subject.title if outcome.subject else "the item"
    target = outcome.target.title if outcome.target else "the target"
    if outcome.tool_name == "folder_add_saved_quiz":
        return f"Added {subject} to {target}."
    if outcome.tool_name == "folder_move_quiz":
        return f"Moved {subject} to {target}."
    if outcome.tool_name == "folder_remove_quiz":
        return f"Removed {subject} from {target}."
    if outcome.tool_name == "folder_delete":
        return f"Deleted {subject} folder."
    if outcome.tool_name == "folder_rename":
        return f"Renamed folder to {subject}."
    if outcome.tool_name == "share_send_email":
        return f"Share link sent to {outcome.recipient or 'the recipient'}."
    if outcome.tool_name == "live_quiz_send_invites":
        if outcome.recipient:
            label = f"Sent {subject} live quiz invite to {outcome.recipient}"
        else:
            count = outcome.count or 0
            label = f"Sent quiz invites to {count} recipients"
        if outcome.failed_count:
            label = f"{label}; {outcome.failed_count} failed"
        return f"{label}."
    return None


def _join_phrases(phrases: list[str]) -> str:
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


def _download_instruction(outcome: ActionOutcome) -> str:
    if outcome.data.get("auto_execute"):
        return "The download should start now; if it does not, use the Download quiz button below."
    return "Click the Download quiz button below to start the download."


def _item_count(data: object) -> int:
    items = data.get("result") if isinstance(data, dict) and "result" in data else data
    return len(items) if isinstance(items, list) else 0


def _folder_match_response(data: dict) -> AssistantFinalResponse:
    query = data.get("query") or "that quiz"
    matches = data.get("matches")
    if not isinstance(matches, list) or not matches:
        return AssistantFinalResponse(message=f"I could not find {query} in your folders.")
    names = sorted({str(item.get("folder_name")) for item in matches if isinstance(item, dict) and item.get("folder_name")})
    location = f"{names[0]} Folder" if len(names) == 1 else (f"{', '.join(names)} Folders" if names else "your folder library")
    return AssistantFinalResponse(message=f"{query} is in {location}.")
