from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from server.app.assistant.error_mapper import (
    AUTH_REQUIRED_CODE,
    VERIFICATION_REQUIRED_CODE,
    assistant_policy_error_detail,
)
from server.app.core.config import settings
from server.app.users.models import UserOut


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    argument_schema: dict[str, Any]
    requires_auth: bool = False
    requires_verified: bool = False
    requires_confirmation: bool = False
    is_write: bool = False

    @property
    def required_arguments(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, definition in self.argument_schema.items()
            if definition.get("required") is True
        )

    def argument_definition(self, name: str) -> dict[str, Any] | None:
        return self.argument_schema.get(name)


TOOL_DEFINITIONS: dict[str, ToolDefinition] = {
    "category_list": ToolDefinition(
        name="category_list",
        description="List all public quiz categories available for browsing.",
        argument_schema={},
    ),
    "category_list_subcategories": ToolDefinition(
        name="category_list_subcategories",
        description="List public subcategories under a known quiz category.",
        argument_schema={
            "category": {
                "type": "string",
                "required": True,
                "description": "Exact category name from category_list or clearly supplied by the user.",
            }
        },
    ),
    "category_list_quiz_types": ToolDefinition(
        name="category_list_quiz_types",
        description="List available question/quiz types for a category and subcategory.",
        argument_schema={
            "category": {
                "type": "string",
                "required": True,
                "description": "Exact category name.",
            },
            "subcategory": {
                "type": "string",
                "required": True,
                "description": "Exact subcategory name.",
            },
        },
    ),
    "category_browse_questions": ToolDefinition(
        name="category_browse_questions",
        description="Browse public category questions from canonical V2 quiz documents.",
        argument_schema={
            "category": {
                "type": "string",
                "required": True,
                "description": "Exact category name.",
            },
            "subcategory": {
                "type": "string",
                "required": True,
                "description": "Exact subcategory name.",
            },
            "question_type": {
                "type": "string",
                "required": True,
                "allowed_values": ["multichoice", "true-false", "short-answer", "open-ended"],
                "aliases": {
                    "multiple-choice": "multichoice",
                    "multiple choice": "multichoice",
                    "mcq": "multichoice",
                    "true or false": "true-false",
                    "true/false": "true-false",
                    "short answer": "short-answer",
                    "open ended": "open-ended",
                },
            },
            "page": {"type": "integer", "required": False, "default": 1},
            "page_size": {"type": "integer", "required": False, "default": 20},
        },
    ),
    "quiz_generate": ToolDefinition(
        name="quiz_generate",
        description=(
            "Generate one new quiz through the existing quiz generation pipeline. Use only when the "
            "user explicitly asks to generate/create/make/build/produce/draft a new quiz or questions. "
            "Do not use for existing saved, history, folder, shared, listed, or artifact quizzes."
        ),
        argument_schema={
            "profession": {
                "type": "string",
                "required": True,
                "description": (
                    "The quiz topic, subject, course, profession, or context. Examples: "
                    "'history of Nigerian geopolitics', 'JavaScript DSA', 'British Empire'."
                ),
            },
            "num_questions": {
                "type": "integer",
                "required": True,
                "description": (
                    "Number of questions in the quiz. In this product, phrases like '4 quizzes' "
                    "usually mean 4 questions unless the user explicitly asks for separate quiz documents."
                ),
                "minimum": 1,
                "maximum": settings.QUIZ_GENERATION_MAX_QUESTIONS,
            },
            "question_type": {
                "type": "string",
                "required": True,
                "allowed_values": ["multichoice", "true-false", "short-answer", "open-ended"],
                "aliases": {
                    "multiple-choice": "multichoice",
                    "multiple choice": "multichoice",
                    "multi-choice": "multichoice",
                    "multi choice": "multichoice",
                    "mcq": "multichoice",
                    "true or false": "true-false",
                    "true/false": "true-false",
                    "short answer": "short-answer",
                    "open ended": "open-ended",
                },
                "description": "Canonical question type. Normalize user wording to one allowed value.",
            },
            "difficulty_level": {
                "type": "string",
                "required": False,
                "default": "easy",
                "description": "Use user-supplied difficulty if present; otherwise omit or use easy.",
            },
            "audience_type": {
                "type": "string",
                "required": False,
                "default": "students",
                "description": "Use user-supplied audience if present; otherwise omit or use students.",
            },
            "custom_instruction": {
                "type": "string",
                "required": False,
                "description": "Extra generation constraint from the user, such as exam board, tone, or coverage.",
            },
        },
        requires_auth=True,
        requires_verified=True,
    ),
    "share_get_quiz": ToolDefinition(
        name="share_get_quiz",
        description="Read a public or shared quiz.",
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id or shared quiz id supplied by the user/artifact/context.",
            }
        },
    ),
    "quiz_get_answers": ToolDefinition(
        name="quiz_get_answers",
        description=(
            "Return the answer key for an authenticated user's owned, generated, saved, "
            "history, or folder quiz. Use when the user asks for answers or answer key."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id from a generated, saved, history, folder, or page-context quiz.",
            }
        },
        requires_auth=True,
        requires_verified=True,
    ),
    "share_create_link": ToolDefinition(
        name="share_create_link",
        description="Create a share link for an owned/private quiz where allowed.",
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id from a generated, saved, history, or shared quiz artifact.",
            }
        },
        requires_auth=True,
    ),
    "share_send_email": ToolDefinition(
        name="share_send_email",
        description=(
            "Send a QuizApp share link to an email recipient. Use after share_create_link when the user asks "
            "to share/send/email a quiz or existing share link to a specific email address."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id from the generated, saved, history, folder, or share artifact.",
            },
            "recipient_email": {
                "type": "string",
                "required": True,
                "description": "Recipient email address supplied by the user.",
            },
            "shareable_link": {
                "type": "string",
                "required": False,
                "description": "Share URL produced by share_create_link or present in recent artifacts.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "quiz_export_link": ToolDefinition(
        name="quiz_export_link",
        description=(
            "Prepare an authenticated export/download action for a quiz. Use when the user asks to download "
            "or export an existing/generated quiz."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id from a generated, saved, history, folder, or share artifact.",
            },
            "format": {
                "type": "string",
                "required": False,
                "allowed_values": ["txt", "json", "pdf", "docx"],
                "description": "Requested export format. If the user does not specify a format, ask them to choose.",
                "choice_prompt": "Choose a file format for the quiz download.",
                "choices": [
                    {"label": "PDF", "value": "pdf"},
                    {"label": "DOCX", "value": "docx"},
                    {"label": "TXT", "value": "txt"},
                    {"label": "JSON", "value": "json"},
                ],
            },
        },
        requires_auth=True,
        requires_verified=True,
    ),
    "live_quiz_get_access_link": ToolDefinition(
        name="live_quiz_get_access_link",
        description=(
            "Get an existing active live quiz access link for an owned quiz. Use when the user asks "
            "whether a quiz already has a live quiz link, access code, attempt link, or participant link."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id from a generated, saved, history, folder, share, or page artifact.",
            }
        },
        requires_auth=True,
        requires_verified=True,
    ),
    "live_quiz_create_access_link": ToolDefinition(
        name="live_quiz_create_access_link",
        description=(
            "Create or reuse a live quiz access link for an owned quiz. The tool returns an existing active "
            "non-expired link when available unless regenerate is true. Use for requests like 'create a live "
            "quiz link', 'generate an attempt link', or 'set up this quiz for participants'."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id from a generated, saved, history, folder, share, or page artifact.",
            },
            "duration": {
                "type": "integer",
                "required": True,
                "description": "Required quiz duration in minutes, explicitly supplied by the user.",
            },
            "access_code_expires_at": {
                "type": "string",
                "required": False,
                "description": "ISO datetime when the participant link expires, if explicitly supplied by the user.",
            },
            "expires_in_hours": {
                "type": "integer",
                "required": False,
                "default": 24,
                "description": "Relative expiration window in hours when no exact expiration datetime is supplied.",
            },
            "regenerate": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Only true when the user explicitly asks to regenerate or replace an existing live link.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "live_quiz_ensure_access_link": ToolDefinition(
        name="live_quiz_ensure_access_link",
        description=(
            "Idempotently get or create a live quiz access link for an owned quiz. Use for requests like "
            "'check if this quiz has a live link; if not create one' or live quiz invite workflows. "
            "If an active non-expired link exists, duration is not needed. If no active link exists, "
            "duration is required before creating a new link."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id or saved quiz id from a generated, saved, history, folder, share, or page artifact.",
            },
            "duration": {
                "type": "integer",
                "required": False,
                "description": "Quiz duration in minutes, explicitly supplied by the user when a new live link must be created.",
            },
            "access_code_expires_at": {
                "type": "string",
                "required": False,
                "description": "ISO datetime when the participant link expires, if explicitly supplied by the user.",
            },
            "expires_in_hours": {
                "type": "integer",
                "required": False,
                "default": 24,
                "description": "Relative expiration window in hours when no exact expiration datetime is supplied.",
            },
            "regenerate": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Only true when the user explicitly asks to regenerate or replace an existing live link.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=False,
        is_write=False,
    ),
    "live_quiz_send_invites": ToolDefinition(
        name="live_quiz_send_invites",
        description=(
            "Send a live quiz access link to one or more recipient emails. Use only after a live quiz link "
            "exists or after live_quiz_create_access_link in the same plan."
        ),
        argument_schema={
            "quiz_id": {
                "type": "string",
                "required": True,
                "description": "Canonical quiz id for the live quiz.",
            },
            "recipient_emails": {
                "type": "array",
                "required": True,
                "description": "One or more recipient email addresses supplied by the user.",
            },
            "live_quiz_link": {
                "type": "string",
                "required": False,
                "description": "Live quiz URL produced by live_quiz_create_access_link or live_quiz_get_access_link.",
            },
            "message": {
                "type": "string",
                "required": False,
                "description": "Optional invite message supplied by the user.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "library_list_saved_quizzes": ToolDefinition(
        name="library_list_saved_quizzes",
        description="List the authenticated user's saved quizzes.",
        argument_schema={
            "limit": {
                "type": "integer",
                "required": False,
                "default": 100,
                "description": "Maximum saved quizzes to return. Use 100 when the user asks for all saved quizzes.",
            }
        },
        requires_auth=True,
    ),
    "library_get_saved_quiz": ToolDefinition(
        name="library_get_saved_quiz",
        description="Get one saved quiz for the authenticated user.",
        argument_schema={
            "saved_quiz_id": {
                "type": "string",
                "required": True,
                "description": "Saved quiz id from library_list_saved_quizzes or a saved_quiz artifact, not quiz_id.",
            }
        },
        requires_auth=True,
    ),
    "library_find_saved_quiz_by_title": ToolDefinition(
        name="library_find_saved_quiz_by_title",
        description=(
            "Find saved quizzes by title for lookup workflows. Use this when the user names a saved quiz "
            "and another action needs saved_quiz_id, such as adding the quiz to a folder. The best match "
            "is returned at top-level as saved_quiz_id for placeholder chaining."
        ),
        argument_schema={
            "title": {
                "type": "string",
                "required": True,
                "description": "Saved quiz title or clear title fragment supplied by the user.",
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 10,
                "description": "Maximum matches to return.",
            },
        },
        requires_auth=True,
    ),
    "library_save_quiz": ToolDefinition(
        name="library_save_quiz",
        description=(
            "Save a quiz to the authenticated user's library. Prefer quiz_id when saving an existing "
            "generated, history, saved, folder, or artifact quiz. Only send title, question_type, and "
            "questions when creating a saved quiz from a raw quiz payload."
        ),
        argument_schema={
            "title": {
                "type": "string",
                "required": False,
                "description": "Quiz title. Optional when quiz_id points to an existing canonical quiz.",
            },
            "question_type": {
                "type": "string",
                "required": False,
                "allowed_values": ["multichoice", "true-false", "short-answer", "open-ended"],
                "description": "Canonical question type from the quiz being saved. Optional when quiz_id is supplied.",
            },
            "questions": {
                "type": "array",
                "required": False,
                "description": "Questions array from quiz_generate or a raw quiz payload. Not required when quiz_id is supplied.",
            },
            "quiz_id": {
                "type": "string",
                "required": False,
                "description": "Canonical quiz id when saving an existing/generated canonical quiz.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        is_write=True,
    ),
    "saved_quiz_rename": ToolDefinition(
        name="saved_quiz_rename",
        description="Rename the display title of one saved quiz in the authenticated user's library.",
        argument_schema={
            "saved_quiz_id": {
                "type": "string",
                "required": True,
                "description": "Saved quiz id from library_list_saved_quizzes, library_find_saved_quiz_by_title, or an artifact.",
            },
            "title": {
                "type": "string",
                "required": True,
                "description": "New saved quiz display title requested by the user.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "saved_quiz_delete": ToolDefinition(
        name="saved_quiz_delete",
        description="Delete one saved quiz reference from the authenticated user's library.",
        argument_schema={
            "saved_quiz_id": {
                "type": "string",
                "required": True,
                "description": "Saved quiz id from library_list_saved_quizzes, library_find_saved_quiz_by_title, or an artifact.",
            }
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "library_list_history": ToolDefinition(
        name="library_list_history",
        description="List the authenticated user's quiz history.",
        argument_schema={
            "limit": {
                "type": "integer",
                "required": False,
                "default": 100,
                "description": "Maximum history records to return. Use 100 when the user asks for all history.",
            }
        },
        requires_auth=True,
    ),
    "library_get_history_detail": ToolDefinition(
        name="library_get_history_detail",
        description="Get one quiz-history detail for the authenticated user.",
        argument_schema={
            "history_id": {
                "type": "string",
                "required": True,
                "description": "History item id from library_list_history or a history artifact.",
            }
        },
        requires_auth=True,
    ),
    "folder_list": ToolDefinition(
        name="folder_list",
        description="List the authenticated user's folders.",
        argument_schema={},
        requires_auth=True,
    ),
    "folder_get": ToolDefinition(
        name="folder_get",
        description="Get one authenticated user folder.",
        argument_schema={
            "folder_id": {
                "type": "string",
                "required": True,
                "description": "Folder id from folder_list or a folder artifact.",
            }
        },
        requires_auth=True,
    ),
    "folder_get_by_name": ToolDefinition(
        name="folder_get_by_name",
        description="Get one authenticated user folder and its quizzes by exact or user-supplied folder name.",
        argument_schema={
            "name": {
                "type": "string",
                "required": True,
                "description": "Folder name supplied by the user, for example 'Physics'.",
            }
        },
        requires_auth=True,
    ),
    "folder_find_quiz_by_title": ToolDefinition(
        name="folder_find_quiz_by_title",
        description=(
            "Find whether a quiz title exists in any authenticated user folder. Use for questions like "
            "'is Specific Heat in any folder?' before trying broader folder reads."
        ),
        argument_schema={
            "title": {
                "type": "string",
                "required": True,
                "description": "Quiz title or clear title fragment supplied by the user.",
            }
        },
        requires_auth=True,
    ),
    "folder_create": ToolDefinition(
        name="folder_create",
        description="Create a folder for the authenticated user.",
        argument_schema={
            "name": {
                "type": "string",
                "required": True,
                "description": "Folder name to create.",
            }
        },
        requires_auth=True,
        requires_verified=True,
        is_write=True,
    ),
    "folder_add_saved_quiz": ToolDefinition(
        name="folder_add_saved_quiz",
        description=(
            "Add an already saved quiz to an authenticated user's folder. This tool requires saved_quiz_id. "
            "If the user only has a generated quiz_id, save it with library_save_quiz first."
        ),
        argument_schema={
            "folder_id": {
                "type": "string",
                "required": True,
                "description": "Folder id from folder_list, folder_get_by_name, or folder_create.",
            },
            "saved_quiz_id": {
                "type": "string",
                "required": True,
                "description": "Saved quiz id from library_list_saved_quizzes or library_save_quiz, not quiz_id.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        is_write=True,
    ),
    "folder_rename": ToolDefinition(
        name="folder_rename",
        description="Rename one folder owned by the authenticated user.",
        argument_schema={
            "folder_id": {
                "type": "string",
                "required": True,
                "description": "Folder id from folder_list, folder_get_by_name, or an artifact.",
            },
            "new_name": {
                "type": "string",
                "required": True,
                "description": "New folder name requested by the user.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "folder_delete": ToolDefinition(
        name="folder_delete",
        description="Delete one folder owned by the authenticated user.",
        argument_schema={
            "folder_id": {
                "type": "string",
                "required": True,
                "description": "Folder id from folder_list, folder_get_by_name, or an artifact.",
            }
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "folder_remove_quiz": ToolDefinition(
        name="folder_remove_quiz",
        description="Remove one quiz item from one of the authenticated user's folders.",
        argument_schema={
            "folder_id": {
                "type": "string",
                "required": True,
                "description": "Folder id containing the quiz item.",
            },
            "folder_item_id": {
                "type": "string",
                "required": True,
                "description": "Folder item id from folder_get, folder_get_by_name, or folder_find_quiz_by_title.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "folder_move_quiz": ToolDefinition(
        name="folder_move_quiz",
        description="Move one quiz item from a source folder to a target folder owned by the authenticated user.",
        argument_schema={
            "folder_item_id": {
                "type": "string",
                "required": True,
                "description": "Folder item id from folder_get, folder_get_by_name, or folder_find_quiz_by_title.",
            },
            "source_folder_id": {
                "type": "string",
                "required": True,
                "description": "Current folder id containing the quiz item.",
            },
            "target_folder_id": {
                "type": "string",
                "required": True,
                "description": "Destination folder id.",
            },
        },
        requires_auth=True,
        requires_verified=True,
        requires_confirmation=True,
        is_write=True,
    ),
    "notification_list": ToolDefinition(
        name="notification_list",
        description="List the authenticated user's notifications. Admin/broadcast notifications are not exposed here.",
        argument_schema={
            "limit": {
                "type": "integer",
                "required": False,
                "default": 20,
                "description": "Maximum notifications to return.",
            },
            "skip": {
                "type": "integer",
                "required": False,
                "default": 0,
                "description": "Pagination offset.",
            },
        },
        requires_auth=True,
    ),
    "notification_mark_read": ToolDefinition(
        name="notification_mark_read",
        description="Mark one authenticated user's notification as read.",
        argument_schema={
            "notification_id": {
                "type": "string",
                "required": True,
                "description": "Notification id from notification_list or a notification artifact.",
            }
        },
        requires_auth=True,
        is_write=True,
    ),
    "notification_delete": ToolDefinition(
        name="notification_delete",
        description="Delete one authenticated user's notification.",
        argument_schema={
            "notification_id": {
                "type": "string",
                "required": True,
                "description": "Notification id from notification_list or a notification artifact.",
            }
        },
        requires_auth=True,
        requires_confirmation=True,
        is_write=True,
    ),
}


def list_tool_definitions() -> list[ToolDefinition]:
    return list(TOOL_DEFINITIONS.values())


def get_tool_definition(tool_name: str) -> ToolDefinition:
    try:
        return TOOL_DEFINITIONS[tool_name]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported assistant tool: {tool_name}",
        )


def enforce_tool_policy(tool_name: str, user: UserOut | None) -> ToolDefinition:
    tool = get_tool_definition(tool_name)
    if tool.requires_auth and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=assistant_policy_error_detail(code=AUTH_REQUIRED_CODE, tool_name=tool_name),
        )
    if tool.requires_verified and user is not None and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=assistant_policy_error_detail(code=VERIFICATION_REQUIRED_CODE, tool_name=tool_name),
        )
    return tool


def should_request_confirmation(tool: ToolDefinition, planner_requires_confirmation: bool) -> bool:
    _ = planner_requires_confirmation
    return bool(
        tool.requires_confirmation
        or (settings.ASSISTANT_REQUIRE_CONFIRMATION_FOR_WRITES and tool.is_write)
    )


def public_tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "arguments": tool.argument_schema,
            "requires_auth": tool.requires_auth,
            "requires_verified": tool.requires_verified,
            "requires_confirmation": tool.requires_confirmation,
            "is_write": tool.is_write,
        }
        for tool in list_tool_definitions()
    ]
