from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from server.app.assistant.artifacts import infer_artifacts_from_results
from server.app.assistant.mcp_client import AssistantMcpClient
from server.app.assistant.model_router import AssistantModelRouter
from server.app.assistant.prompts import (
    build_executor_prompt,
    build_final_response_prompt,
    build_general_response_prompt,
    build_plan_repair_prompt,
    build_planner_prompt,
)
from server.app.assistant.pending_runs import AssistantRunStore, PendingAssistantRun, RedisAssistantRunStore
from server.app.assistant.schemas import (
    AssistantAction,
    AssistantArtifact,
    AssistantChatResponse,
    AssistantFinalResponse,
    ExecutorDecision,
    PlanStep,
    PlannerDecision,
    ToolResult,
)
from server.app.assistant.tool_policy import enforce_tool_policy, get_tool_definition, should_request_confirmation
from server.app.core.config import settings
from server.app.users.models import UserOut


PLACEHOLDER_PATTERN = re.compile(r"^\$steps\.([^.]+)\.result\.([A-Za-z0-9_]+)$")
CONTEXT_PATTERN = re.compile(r"^\$context\.([A-Za-z0-9_]+)$")
QUIZ_NOUN_PATTERN = r"(?:quiz(?:zes|ze)?|questions?|tests?|assessments?)"
GENERATION_VERBS_PATTERN = r"(?:generate|create|make|build|produce|draft|set up)"
GENERATION_INTENT_PATTERN = re.compile(
    rf"\b{GENERATION_VERBS_PATTERN}\b.*\b{QUIZ_NOUN_PATTERN}\b"
    rf"|\b{QUIZ_NOUN_PATTERN}\b.*\b{GENERATION_VERBS_PATTERN}\b",
    re.IGNORECASE,
)
QUIZ_GENERATE_REQUIRED_FIELDS = ("profession", "num_questions", "question_type")
QUESTION_TYPE_PATTERNS = (
    (re.compile(r"\b(multiple[-\s]*choice|multi[-\s]*choice|multichoice|mcq)\b", re.IGNORECASE), "multichoice"),
    (re.compile(r"\b(true[-\s]*/?[-\s]*false|true\s+or\s+false)\b", re.IGNORECASE), "true-false"),
    (re.compile(r"\b(open[-\s]*ended|essay)\b", re.IGNORECASE), "open-ended"),
    (re.compile(r"\b(short[-\s]*answer)\b", re.IGNORECASE), "short-answer"),
)
EXPORT_FORMAT_PATTERNS = (
    (re.compile(r"\bpdf\b", re.IGNORECASE), "pdf"),
    (re.compile(r"\bdocx\b|\bword\s+document\b", re.IGNORECASE), "docx"),
    (re.compile(r"\btxt\b|\btext\s+file\b", re.IGNORECASE), "txt"),
    (re.compile(r"\bjson\b", re.IGNORECASE), "json"),
)
DOWNLOAD_INTENT_PATTERN = re.compile(r"\b(download|export)\b", re.IGNORECASE)
CANONICAL_ID_PATTERN = re.compile(r"^[a-f0-9]{24}$", re.IGNORECASE)
LIVE_QUIZ_LINK_INTENT_PATTERN = re.compile(
    r"\blive\s+quiz\b.*\b(link|access\s+code|attempt\s+link|participant\s+link|invite)\b"
    r"|\b(link|access\s+code|attempt\s+link|participant\s+link|invite)\b.*\blive\s+quiz\b"
    r"|\blive\s+(?:link|access\s+link|attempt\s+link|participant\s+link)\b.*\bquiz\b"
    r"|\bquiz\b.*\blive\s+(?:link|access\s+link|attempt\s+link|participant\s+link)\b",
    re.IGNORECASE,
)
LIVE_QUIZ_LINK_ONLY_CREATION_PATTERN = re.compile(
    rf"\b{GENERATION_VERBS_PATTERN}\b\s+(?:a|an|the|new|valid|active)?\s*"
    r"(?:live\s+)?(?:quiz\s+)?(?:link|access\s+code|attempt\s+link|participant\s+link|invite)\b"
    rf"|\b{GENERATION_VERBS_PATTERN}\b\s+(?:a|an|the|new|valid|active)?\s*live\s+quiz\s+"
    r"(?:link|access\s+code|attempt\s+link|participant\s+link|invite)\b",
    re.IGNORECASE,
)
LIVE_QUIZ_CREATE_INTENT_PATTERN = re.compile(
    r"\b(create|generate|make|build|set\s+up|new|regenerate|replace)\b",
    re.IGNORECASE,
)
EMAIL_ADDRESS_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.IGNORECASE)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
LIVE_QUIZ_DURATION_VALUE_PATTERNS = (
    re.compile(
        r"\b(?:duration|quiz\s+duration)\b\D{0,30}(\d+)\s*(minutes?|mins?|hours?|hrs?)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:use|set|make|give)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+(?:as\s+)?(?:the\s+)?(?:quiz\s+)?duration\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:use|set|make|give)\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\b", re.IGNORECASE),
    re.compile(r"\bfor\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\b", re.IGNORECASE),
    re.compile(
        r"\bwith\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+(?:quiz\s+)?duration\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d+)\s*[- ]?(minute|min|hour|hr)\s+(?:quiz|live\s+quiz|duration)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(\d+)\s*(minutes?|mins?|hours?|hrs?)\s*[.?!]?\s*$", re.IGNORECASE),
)
FOLDER_ADD_INTENT_PATTERN = re.compile(
    r"\b(add|save|put|place|move)\b.*\bfolder\b|\bfolder\b.*\b(add|save|put|place|move)\b",
    re.IGNORECASE,
)
FOLDER_NAME_PATTERN = re.compile(
    r"\b(?:to|in|into)\s+(?:my|the|a|an)?\s*([A-Za-z0-9][A-Za-z0-9 &_-]*?)\s+folder\b",
    re.IGNORECASE,
)
LIVE_QUIZ_TOOLS = {
    "live_quiz_get_access_link",
    "live_quiz_create_access_link",
    "live_quiz_ensure_access_link",
    "live_quiz_send_invites",
}
REQUIRED_TOOL_ARGUMENTS = {
    "quiz_generate": QUIZ_GENERATE_REQUIRED_FIELDS,
    "category_list_subcategories": ("category",),
    "category_list_quiz_types": ("category", "subcategory"),
    "category_browse_questions": ("category", "subcategory", "question_type"),
    "share_get_quiz": ("quiz_id",),
    "share_create_link": ("quiz_id",),
    "share_send_email": ("quiz_id", "recipient_email"),
    "quiz_export_link": ("quiz_id",),
    "live_quiz_get_access_link": ("quiz_id",),
    "live_quiz_create_access_link": ("quiz_id", "duration"),
    "live_quiz_ensure_access_link": ("quiz_id",),
    "live_quiz_send_invites": ("quiz_id", "recipient_emails"),
    "library_get_saved_quiz": ("saved_quiz_id",),
    "library_find_saved_quiz_by_title": ("title",),
    "library_save_quiz": ("title", "question_type", "questions"),
    "saved_quiz_rename": ("saved_quiz_id", "title"),
    "saved_quiz_delete": ("saved_quiz_id",),
    "library_get_history_detail": ("history_id",),
    "folder_get": ("folder_id",),
    "folder_get_by_name": ("name",),
    "folder_find_quiz_by_title": ("title",),
    "folder_create": ("name",),
    "folder_add_saved_quiz": ("folder_id", "saved_quiz_id"),
    "folder_rename": ("folder_id", "new_name"),
    "folder_delete": ("folder_id",),
    "folder_remove_quiz": ("folder_id", "folder_item_id"),
    "folder_move_quiz": ("folder_item_id", "source_folder_id", "target_folder_id"),
    "notification_mark_read": ("notification_id",),
    "notification_delete": ("notification_id",),
}
SELECTABLE_TOOL_ARGUMENTS = {
    "quiz_export_link": {
        "format": {
            "label": "export format",
            "message": "Choose a file format for the quiz download.",
            "choices": [
                {"label": "PDF", "value": "pdf"},
                {"label": "DOCX", "value": "docx"},
                {"label": "TXT", "value": "txt"},
                {"label": "JSON", "value": "json"},
            ],
        }
    }
}


@dataclass
class AssistantRun:
    run_id: str
    user_id: str | None
    user_message: str
    status: str = "planning"
    plan: list[PlanStep] = field(default_factory=list)
    current_step_index: int = 0
    tool_results: list[ToolResult] = field(default_factory=list)
    pending_confirmation: AssistantAction | None = None
    page_context: dict[str, Any] | None = None
    recent_artifacts: list[dict[str, Any]] | None = None


class AssistantOrchestrator:
    def __init__(
        self,
        *,
        model_router: AssistantModelRouter,
        mcp_client: AssistantMcpClient,
        pending_run_store: AssistantRunStore | None = None,
    ):
        self.model_router = model_router
        self.mcp_client = mcp_client
        self.pending_run_store = pending_run_store or RedisAssistantRunStore()

    async def run(
        self,
        *,
        message: str,
        conversation_id: str,
        page_context: dict[str, Any] | None,
        recent_messages: list[dict[str, Any]] | None,
        recent_artifacts: list[dict[str, Any]] | None,
        user: UserOut | None,
        authorization_header: str | None,
    ) -> AssistantChatResponse:
        pending_missing_run = await self.pending_run_store.pop_for_conversation(
            user_id=str(user.id) if user else None,
            conversation_id=conversation_id,
            pending_mode="missing_arguments",
        )
        if pending_missing_run is not None:
            return await self._resume_pending_run_from_message(
                pending_run=pending_missing_run,
                message=message,
                user=user,
                authorization_header=authorization_header,
            )

        run = AssistantRun(
            run_id=str(uuid4()),
            user_id=str(user.id) if user else None,
            user_message=message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        planner = await self.model_router.plan(
            build_planner_prompt(
                message,
                page_context,
                recent_messages=recent_messages,
                recent_artifacts=recent_artifacts,
            )
        )
        planner = await self._validate_and_repair_plan(
            planner=planner,
            message=message,
            page_context=page_context,
            recent_messages=recent_messages,
            recent_artifacts=recent_artifacts,
        )

        if not planner.needs_tools or not planner.steps:
            final = await self.model_router.final_response(
                build_general_response_prompt(message, page_context)
            )
            return AssistantChatResponse(
                message=final.message,
                conversation_id=conversation_id,
                artifacts=final.artifacts,
            )

        unresolved_intents = self._missing_explicit_workflow_intents(planner.steps, message)
        if unresolved_intents:
            return AssistantChatResponse(
                message=self._plan_clarification_message(unresolved_intents),
                conversation_id=conversation_id,
                artifacts=[],
            )

        self._validate_plan(planner)
        run.plan = planner.steps[: settings.ASSISTANT_MAX_TOOL_CALLS]
        run.status = "executing"

        for index, step in enumerate(run.plan):
            run.current_step_index = index
            tool = enforce_tool_policy(step.tool_name, user)
            resolved_arguments = self._resolve_arguments(
                step.arguments,
                run=run,
                user=user,
            )

            if self._needs_executor_repair(resolved_arguments):
                executor = await self._repair_step_arguments(
                    step=step,
                    message=message,
                    page_context=page_context,
                    previous_results=self._dump_results(run),
                )
                if executor.tool_name != step.tool_name:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Assistant executor selected a different tool than the planner.",
                    )
                resolved_arguments = self._resolve_arguments(
                    executor.arguments,
                    run=run,
                    user=user,
                )

            if self._needs_executor_repair(resolved_arguments):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Could not resolve arguments for assistant step {step.step_id}.",
                )

            preflight_response = await self._preflight_step(
                step=step,
                arguments=resolved_arguments,
                run=run,
                conversation_id=conversation_id,
                user=user,
            )
            if preflight_response is not None:
                return preflight_response

            blocked_message = self._blocked_tool_call_message(
                tool_name=step.tool_name,
                arguments=resolved_arguments,
                user_message=message,
            )
            if blocked_message:
                return AssistantChatResponse(
                    message=blocked_message,
                    conversation_id=conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results),
                )

            if should_request_confirmation(tool, step.requires_confirmation):
                step.arguments = resolved_arguments
                action = AssistantAction(
                    type="confirm",
                    label=self._confirmation_label(step.tool_name),
                    run_id=run.run_id,
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    arguments=resolved_arguments,
                )
                run.status = "waiting_confirmation"
                run.pending_confirmation = action
                await self.pending_run_store.save(
                    self._pending_run_snapshot(run, conversation_id=conversation_id, current_step_index=index)
                )
                return AssistantChatResponse(
                    message=self._confirmation_message(step.tool_name, resolved_arguments, run),
                    conversation_id=conversation_id,
                    actions=[action],
                    artifacts=[],
                )

            tool_result = await self.mcp_client.call_tool(
                tool_name=step.tool_name,
                arguments=resolved_arguments,
                authorization_header=authorization_header,
            )
            normalized_result = self._normalize_tool_result(
                step_id=step.step_id,
                tool_name=step.tool_name,
                raw_result=tool_result,
            )
            duration_response = await self._duration_required_response_for_result(
                result=normalized_result,
                step=step,
                run=run,
                conversation_id=conversation_id,
            )
            if duration_response is not None:
                return duration_response
            run.tool_results.append(normalized_result)
            if not normalized_result.ok:
                return AssistantChatResponse(
                    message=self._tool_error_message(normalized_result),
                    conversation_id=conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results),
                )

        run.status = "completed"
        final = self._deterministic_final_response(run) or await self._compose_final_response(message, run)
        return AssistantChatResponse(
            message=final.message,
            conversation_id=conversation_id,
            artifacts=self._merge_artifacts(
                final.artifacts,
                self._infer_artifacts_from_results(
                    run.tool_results,
                    suppress_internal_lookup=True,
                    suppress_final_status_tools={"live_quiz_send_invites"},
                ),
            ),
        )

    async def run_confirmed_action(
        self,
        *,
        message: str,
        conversation_id: str,
        run_id: str | None,
        step_id: str | None,
        action_type: str | None,
        tool_name: str,
        arguments: dict[str, Any],
        user: UserOut | None,
        authorization_header: str | None,
    ) -> AssistantChatResponse:
        pending_run: PendingAssistantRun | None = None
        if run_id:
            pending_run = await self.pending_run_store.pop(
                run_id=run_id,
                user_id=str(user.id) if user else None,
                conversation_id=conversation_id,
            )

        if pending_run is not None:
            return await self._resume_pending_run(
                pending_run=pending_run,
                confirmed_step_id=step_id,
                confirmed_action_type=action_type,
                confirmed_tool_name=tool_name,
                confirmed_arguments=arguments,
                user=user,
                authorization_header=authorization_header,
            )
        if run_id:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Assistant confirmation expired. Please repeat the request.",
            )

        enforce_tool_policy(tool_name, user)
        tool_result = await self.mcp_client.call_tool(
            tool_name=tool_name,
            arguments=arguments,
            authorization_header=authorization_header,
        )
        normalized = self._normalize_tool_result(
            step_id=step_id or "confirmed_step",
            tool_name=tool_name,
            raw_result=tool_result,
        )
        if action_type == "choice" and tool_name == "quiz_export_link":
            normalized.data["auto_execute"] = True
        final = self._deterministic_final_response_for_results([normalized]) or await self.model_router.final_response(
            build_final_response_prompt(
                message=message,
                tool_name=tool_name,
                tool_result=normalized.model_dump(mode="json"),
                run_results=[normalized.model_dump(mode="json")],
            )
        )
        return AssistantChatResponse(
            message=final.message,
            conversation_id=conversation_id,
            artifacts=self._merge_artifacts(
                final.artifacts,
                self._infer_artifacts_from_results(
                    [normalized],
                    suppress_final_status_tools={"live_quiz_send_invites"},
                ),
            ),
        )

    async def _resume_pending_run_from_message(
        self,
        *,
        pending_run: PendingAssistantRun,
        message: str,
        user: UserOut | None,
        authorization_header: str | None,
    ) -> AssistantChatResponse:
        run = AssistantRun(
            run_id=pending_run.run_id,
            user_id=pending_run.user_id,
            user_message=pending_run.message,
            status="executing",
            plan=pending_run.plan,
            current_step_index=pending_run.current_step_index,
            tool_results=pending_run.tool_results,
            page_context=pending_run.page_context,
            recent_artifacts=pending_run.recent_artifacts,
        )
        if run.current_step_index >= len(run.plan):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Assistant continuation no longer matches an active step.",
            )

        step = run.plan[run.current_step_index]
        missing_arguments = pending_run.missing_arguments or self._missing_required_tool_arguments(
            step.tool_name,
            self._resolve_arguments(step.arguments, run=run, user=user),
        )
        supplied_arguments = self._arguments_from_user_message_for_missing_fields(
            tool_name=step.tool_name,
            missing_arguments=missing_arguments,
            message=message,
        )
        if supplied_arguments:
            step.arguments = {**step.arguments, **supplied_arguments}
            run.user_message = f"{run.user_message}\nFollow-up details: {message}"

        if step.tool_name in LIVE_QUIZ_TOOLS:
            run.plan = self._normalize_live_quiz_identity(
                run.plan,
                run.user_message,
                page_context=run.page_context,
                recent_artifacts=run.recent_artifacts,
            )

        run.current_step_index = self._first_unexecuted_step_index(run)
        if run.current_step_index >= len(run.plan):
            final = self._deterministic_final_response(run) or await self._compose_final_response(run.user_message, run)
            return AssistantChatResponse(
                message=final.message,
                conversation_id=pending_run.conversation_id,
                artifacts=self._merge_artifacts(
                    final.artifacts,
                    self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
                ),
            )

        step = run.plan[run.current_step_index]
        resolved_arguments = self._resolve_arguments(step.arguments, run=run, user=user)
        still_missing = self._missing_required_tool_arguments(step.tool_name, resolved_arguments)
        if still_missing:
            step.arguments = resolved_arguments
            await self.pending_run_store.save(
                self._pending_run_snapshot(
                    run,
                    conversation_id=pending_run.conversation_id,
                    current_step_index=run.current_step_index,
                    pending_mode="missing_arguments",
                    missing_arguments=still_missing,
                )
            )
            return AssistantChatResponse(
                message=self._missing_tool_argument_message(step.tool_name, still_missing),
                conversation_id=pending_run.conversation_id,
                artifacts=[],
            )

        self._validate_plan(run.plan)
        return await self._execute_run_from_current_step(
            run=run,
            conversation_id=pending_run.conversation_id,
            user=user,
            authorization_header=authorization_header,
        )

    async def _execute_run_from_current_step(
        self,
        *,
        run: AssistantRun,
        conversation_id: str,
        user: UserOut | None,
        authorization_header: str | None,
    ) -> AssistantChatResponse:
        for index in range(run.current_step_index, len(run.plan)):
            run.current_step_index = index
            step = run.plan[index]
            tool = enforce_tool_policy(step.tool_name, user)
            resolved_arguments = self._resolve_arguments(step.arguments, run=run, user=user)

            if self._needs_executor_repair(resolved_arguments):
                executor = await self._repair_step_arguments(
                    step=step,
                    message=run.user_message,
                    page_context=run.page_context,
                    previous_results=self._dump_results(run),
                )
                if executor.tool_name != step.tool_name:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Assistant executor selected a different tool than the planner.",
                    )
                resolved_arguments = self._resolve_arguments(executor.arguments, run=run, user=user)

            if self._needs_executor_repair(resolved_arguments):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Could not resolve arguments for assistant step {step.step_id}.",
                )

            preflight_response = await self._preflight_step(
                step=step,
                arguments=resolved_arguments,
                run=run,
                conversation_id=conversation_id,
                user=user,
            )
            if preflight_response is not None:
                return preflight_response

            blocked_message = self._blocked_tool_call_message(
                tool_name=step.tool_name,
                arguments=resolved_arguments,
                user_message=run.user_message,
            )
            if blocked_message:
                return AssistantChatResponse(
                    message=blocked_message,
                    conversation_id=conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
                )

            if should_request_confirmation(tool, step.requires_confirmation):
                step.arguments = resolved_arguments
                action = AssistantAction(
                    type="confirm",
                    label=self._confirmation_label(step.tool_name),
                    run_id=run.run_id,
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    arguments=resolved_arguments,
                )
                run.status = "waiting_confirmation"
                run.pending_confirmation = action
                await self.pending_run_store.save(
                    self._pending_run_snapshot(
                        run,
                        conversation_id=conversation_id,
                        current_step_index=index,
                    )
                )
                return AssistantChatResponse(
                    message=self._confirmation_message(step.tool_name, resolved_arguments, run),
                    conversation_id=conversation_id,
                    actions=[action],
                    artifacts=[],
                )

            tool_result = await self.mcp_client.call_tool(
                tool_name=step.tool_name,
                arguments=resolved_arguments,
                authorization_header=authorization_header,
            )
            normalized_result = self._normalize_tool_result(
                step_id=step.step_id,
                tool_name=step.tool_name,
                raw_result=tool_result,
            )
            duration_response = await self._duration_required_response_for_result(
                result=normalized_result,
                step=step,
                run=run,
                conversation_id=conversation_id,
            )
            if duration_response is not None:
                return duration_response
            run.tool_results.append(normalized_result)
            if not normalized_result.ok:
                return AssistantChatResponse(
                    message=self._tool_error_message(normalized_result),
                    conversation_id=conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
                )

        run.status = "completed"
        final = self._deterministic_final_response(run) or await self._compose_final_response(run.user_message, run)
        return AssistantChatResponse(
            message=final.message,
            conversation_id=conversation_id,
            artifacts=self._merge_artifacts(
                final.artifacts,
                self._infer_artifacts_from_results(
                    run.tool_results,
                    suppress_internal_lookup=True,
                    suppress_final_status_tools={"live_quiz_send_invites"},
                ),
            ),
        )

    async def _resume_pending_run(
        self,
        *,
        pending_run: PendingAssistantRun,
        confirmed_step_id: str | None,
        confirmed_action_type: str | None,
        confirmed_tool_name: str,
        confirmed_arguments: dict[str, Any],
        user: UserOut | None,
        authorization_header: str | None,
    ) -> AssistantChatResponse:
        run = AssistantRun(
            run_id=pending_run.run_id,
            user_id=pending_run.user_id,
            user_message=pending_run.message,
            status="executing",
            plan=pending_run.plan,
            current_step_index=pending_run.current_step_index,
            tool_results=pending_run.tool_results,
            page_context=pending_run.page_context,
            recent_artifacts=pending_run.recent_artifacts,
        )
        if run.current_step_index >= len(run.plan):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Assistant confirmation no longer matches an active step.",
            )

        confirmed_step = run.plan[run.current_step_index]
        if confirmed_step_id and confirmed_step.step_id != confirmed_step_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assistant confirmation does not match the pending step.",
            )
        if confirmed_step.tool_name != confirmed_tool_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assistant confirmation does not match the pending tool.",
            )

        planned_arguments = self._resolve_arguments(
            confirmed_step.arguments,
            run=run,
            user=user,
        )
        submitted_arguments = self._resolve_arguments(
            confirmed_arguments,
            run=run,
            user=user,
        )
        confirmed_arguments = self._merge_selectable_arguments(
            tool_name=confirmed_step.tool_name,
            planned_arguments=planned_arguments,
            submitted_arguments=submitted_arguments,
        )
        if self._needs_executor_repair(confirmed_arguments):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not resolve arguments for assistant step {confirmed_step.step_id}.",
            )

        enforce_tool_policy(confirmed_tool_name, user)
        tool_result = await self.mcp_client.call_tool(
            tool_name=confirmed_tool_name,
            arguments=confirmed_arguments,
            authorization_header=authorization_header,
        )
        normalized_result = self._normalize_tool_result(
            step_id=confirmed_step.step_id,
            tool_name=confirmed_tool_name,
            raw_result=tool_result,
        )
        duration_response = await self._duration_required_response_for_result(
            result=normalized_result,
            step=confirmed_step,
            run=run,
            conversation_id=pending_run.conversation_id,
        )
        if duration_response is not None:
            return duration_response
        if confirmed_action_type == "choice" and confirmed_tool_name == "quiz_export_link":
            normalized_result.data["auto_execute"] = True
        run.tool_results.append(normalized_result)
        if not normalized_result.ok:
            return AssistantChatResponse(
                message=self._tool_error_message(normalized_result),
                conversation_id=pending_run.conversation_id,
                artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
            )

        for index in range(run.current_step_index + 1, len(run.plan)):
            run.current_step_index = index
            step = run.plan[index]
            tool = enforce_tool_policy(step.tool_name, user)
            resolved_arguments = self._resolve_arguments(
                step.arguments,
                run=run,
                user=user,
            )

            if self._needs_executor_repair(resolved_arguments):
                executor = await self._repair_step_arguments(
                    step=step,
                    message=pending_run.message,
                    page_context=None,
                    previous_results=self._dump_results(run),
                )
                if executor.tool_name != step.tool_name:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Assistant executor selected a different tool than the planner.",
                    )
                resolved_arguments = self._resolve_arguments(
                    executor.arguments,
                    run=run,
                    user=user,
                )

            if self._needs_executor_repair(resolved_arguments):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Could not resolve arguments for assistant step {step.step_id}.",
                )

            preflight_response = await self._preflight_step(
                step=step,
                arguments=resolved_arguments,
                run=run,
                conversation_id=pending_run.conversation_id,
                user=user,
            )
            if preflight_response is not None:
                return preflight_response

            blocked_message = self._blocked_tool_call_message(
                tool_name=step.tool_name,
                arguments=resolved_arguments,
                user_message=pending_run.message,
            )
            if blocked_message:
                return AssistantChatResponse(
                    message=blocked_message,
                    conversation_id=pending_run.conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
                )

            if should_request_confirmation(tool, step.requires_confirmation):
                step.arguments = resolved_arguments
                action = AssistantAction(
                    type="confirm",
                    label=self._confirmation_label(step.tool_name),
                    run_id=run.run_id,
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    arguments=resolved_arguments,
                )
                run.status = "waiting_confirmation"
                run.pending_confirmation = action
                await self.pending_run_store.save(
                    self._pending_run_snapshot(
                        run,
                        conversation_id=pending_run.conversation_id,
                        current_step_index=index,
                    )
                )
                return AssistantChatResponse(
                    message=self._confirmation_message(step.tool_name, resolved_arguments, run),
                    conversation_id=pending_run.conversation_id,
                    actions=[action],
                    artifacts=[],
                )

            tool_result = await self.mcp_client.call_tool(
                tool_name=step.tool_name,
                arguments=resolved_arguments,
                authorization_header=authorization_header,
            )
            normalized_result = self._normalize_tool_result(
                step_id=step.step_id,
                tool_name=step.tool_name,
                raw_result=tool_result,
            )
            duration_response = await self._duration_required_response_for_result(
                result=normalized_result,
                step=step,
                run=run,
                conversation_id=pending_run.conversation_id,
            )
            if duration_response is not None:
                return duration_response
            run.tool_results.append(normalized_result)
            if not normalized_result.ok:
                return AssistantChatResponse(
                    message=self._tool_error_message(normalized_result),
                    conversation_id=pending_run.conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
                )

        run.status = "completed"
        final = self._deterministic_final_response(run) or await self._compose_final_response(pending_run.message, run)
        return AssistantChatResponse(
            message=final.message,
            conversation_id=pending_run.conversation_id,
            artifacts=self._merge_artifacts(
                final.artifacts,
                self._infer_artifacts_from_results(
                    run.tool_results,
                    suppress_internal_lookup=True,
                    suppress_final_status_tools={"live_quiz_send_invites"},
                ),
            ),
        )

    def _validate_plan(self, planner: PlannerDecision | list[PlanStep]) -> None:
        steps = planner.steps if isinstance(planner, PlannerDecision) else planner
        if len(steps) > settings.ASSISTANT_MAX_TOOL_CALLS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Assistant plan has too many steps. "
                    f"Maximum is {settings.ASSISTANT_MAX_TOOL_CALLS}."
                ),
            )
        seen: set[str] = set()
        for step in steps:
            if step.step_id in seen:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Duplicate assistant step id: {step.step_id}",
                )
            missing_dependencies = [dependency for dependency in step.depends_on if dependency not in seen]
            if missing_dependencies:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Assistant step {step.step_id} depends on unknown or future steps: "
                        f"{', '.join(missing_dependencies)}"
                    ),
                )
            seen.add(step.step_id)
            get_tool_definition(step.tool_name)

    def _pending_run_snapshot(
        self,
        run: AssistantRun,
        *,
        conversation_id: str,
        current_step_index: int | None = None,
        pending_mode: str | None = None,
        missing_arguments: list[str] | None = None,
    ) -> PendingAssistantRun:
        return PendingAssistantRun(
            run_id=run.run_id,
            user_id=run.user_id,
            conversation_id=conversation_id,
            message=run.user_message,
            plan=run.plan,
            current_step_index=run.current_step_index if current_step_index is None else current_step_index,
            tool_results=run.tool_results,
            page_context=run.page_context,
            recent_artifacts=run.recent_artifacts,
            pending_mode=pending_mode,
            missing_arguments=missing_arguments or [],
        )

    async def _duration_required_response_for_result(
        self,
        *,
        result: ToolResult,
        step: PlanStep,
        run: AssistantRun,
        conversation_id: str,
    ) -> AssistantChatResponse | None:
        if result.tool_name != "live_quiz_ensure_access_link" or not result.data.get("requires_duration"):
            return None

        step.arguments = {
            **step.arguments,
            "quiz_id": result.data.get("quiz_id") or step.arguments.get("quiz_id"),
        }
        await self.pending_run_store.save(
            self._pending_run_snapshot(
                run,
                conversation_id=conversation_id,
                current_step_index=run.current_step_index,
                pending_mode="missing_arguments",
                missing_arguments=["duration"],
            )
        )
        return AssistantChatResponse(
            message="I need the live quiz duration before I can create the link.",
            conversation_id=conversation_id,
            artifacts=[],
        )

    async def _validate_and_repair_plan(
        self,
        *,
        planner: PlannerDecision,
        message: str,
        page_context: dict[str, Any] | None,
        recent_messages: list[dict[str, Any]] | None,
        recent_artifacts: list[dict[str, Any]] | None,
    ) -> PlannerDecision:
        planner = self._harden_plan_for_request(
            planner,
            message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        missing_intents = self._missing_explicit_workflow_intents(planner.steps, message)
        if not missing_intents:
            return planner

        repaired = await self.model_router.plan(
            build_plan_repair_prompt(
                message=message,
                missing_intents=missing_intents,
                current_plan=[step.model_dump(mode="json") for step in planner.steps],
                page_context=page_context,
                recent_messages=recent_messages,
                recent_artifacts=recent_artifacts,
            )
        )
        repaired = self._harden_plan_for_request(
            repaired,
            message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        repaired_missing = self._missing_explicit_workflow_intents(repaired.steps, message)
        if len(repaired_missing) < len(missing_intents):
            return repaired
        return planner

    def _harden_plan_for_request(
        self,
        planner: PlannerDecision,
        message: str,
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> PlannerDecision:
        planner.steps = self._normalize_question_type_arguments(planner.steps)
        planner.steps = self._normalize_export_formats(planner.steps, message)
        planner.steps = self._normalize_live_quiz_duration(planner.steps, message)
        planner.steps = self._normalize_live_quiz_ensure_workflow(planner.steps, message)
        planner.steps = self._normalize_live_quiz_identity(
            planner.steps,
            message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        planner.steps = self._complete_generated_quiz_workflow(planner.steps, message)
        planner.needs_tools = bool(planner.steps)
        return planner

    def _normalize_question_type_arguments(self, steps: list[PlanStep]) -> list[PlanStep]:
        for step in steps:
            question_type = step.arguments.get("question_type")
            if not isinstance(question_type, str):
                continue
            normalized = self._canonical_question_type_from_text(question_type)
            if normalized is not None:
                step.arguments["question_type"] = normalized
        return steps

    def _normalize_live_quiz_ensure_workflow(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        tool_names = {step.tool_name for step in steps}
        wants_conditional_create = bool(
            LIVE_QUIZ_LINK_INTENT_PATTERN.search(message)
            and re.search(r"\b(if\s+not|otherwise|create\s+(?:one|it|a\s+link)|send|email|invite)\b", message, re.IGNORECASE)
        )
        if not wants_conditional_create and "live_quiz_send_invites" not in tool_names:
            return steps

        ensure_step: PlanStep | None = None
        normalized_steps: list[PlanStep] = []
        for step in steps:
            if step.tool_name in {"live_quiz_get_access_link", "live_quiz_create_access_link"}:
                if ensure_step is None:
                    ensure_step = PlanStep(
                        step_id=step.step_id,
                        tool_name="live_quiz_ensure_access_link",
                        arguments=dict(step.arguments),
                        requires_confirmation=False,
                        depends_on=list(step.depends_on),
                        reason=step.reason,
                    )
                    normalized_steps.append(ensure_step)
                continue
            normalized_steps.append(step)

        if ensure_step is None:
            return steps

        for step in normalized_steps:
            if step.tool_name != "live_quiz_send_invites":
                continue
            if "live_quiz_link" not in step.arguments:
                step.arguments["live_quiz_link"] = f"$steps.{ensure_step.step_id}.result.live_quiz_link"
            if ensure_step.step_id not in step.depends_on:
                step.depends_on = [*step.depends_on, ensure_step.step_id]

        return normalized_steps

    def _missing_explicit_workflow_intents(self, steps: list[PlanStep], message: str) -> list[str]:
        tool_names = {step.tool_name for step in steps}
        missing: list[str] = []
        if self._message_explicitly_requests_generation(message) and "quiz_generate" not in tool_names:
            missing.append("generate_quiz")
        if DOWNLOAD_INTENT_PATTERN.search(message) and "quiz_export_link" not in tool_names:
            missing.append("download_quiz")
        if LIVE_QUIZ_LINK_INTENT_PATTERN.search(message) and not (tool_names & LIVE_QUIZ_TOOLS):
            if LIVE_QUIZ_CREATE_INTENT_PATTERN.search(message):
                missing.append("create_live_quiz_link")
            else:
                missing.append("get_live_quiz_link")

        folder_name = self._folder_name_from_message(message)
        wants_folder_add = bool(folder_name and FOLDER_ADD_INTENT_PATTERN.search(message))
        if wants_folder_add and "folder_add_saved_quiz" not in tool_names:
            missing.append("add_quiz_to_folder")
        return missing

    def _plan_clarification_message(self, missing_intents: list[str]) -> str:
        readable = {
            "generate_quiz": "generate the quiz",
            "download_quiz": "prepare the download",
            "add_quiz_to_folder": "add the quiz to the folder",
            "create_live_quiz_link": "create the live quiz link",
            "get_live_quiz_link": "check the live quiz link",
        }
        missing = ", ".join(readable.get(intent, intent) for intent in missing_intents)
        return f"I need a bit more detail before I can {missing}. Please restate the request with the quiz and target details."

    def _normalize_export_formats(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        requested_format = self._explicit_export_format_from_message(message)
        allow_context_format = bool(re.search(r"\b(same|previous|again)\s+format\b", message, re.IGNORECASE))
        for step in steps:
            if step.tool_name != "quiz_export_link":
                continue
            if requested_format:
                step.arguments["format"] = requested_format
            elif not allow_context_format:
                step.arguments.pop("format", None)
        return steps

    def _complete_generated_quiz_workflow(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        generate_step = self._first_step_with_tool(steps, "quiz_generate")
        if generate_step is None:
            return steps

        completed_steps = list(steps)
        folder_name = self._folder_name_from_message(message)
        wants_folder_add = bool(folder_name and FOLDER_ADD_INTENT_PATTERN.search(message))
        wants_download = bool(DOWNLOAD_INTENT_PATTERN.search(message))
        wants_live_quiz_link = bool(LIVE_QUIZ_LINK_INTENT_PATTERN.search(message))
        recipient_emails = self._email_addresses_from_message(message)
        requested_format = self._explicit_export_format_from_message(message)
        requested_duration = self._explicit_live_quiz_duration_from_message(message)

        save_step = self._first_step_with_tool(completed_steps, "library_save_quiz")
        if wants_folder_add and save_step is None:
            save_step = PlanStep(
                step_id=self._next_step_id(completed_steps),
                tool_name="library_save_quiz",
                arguments={
                    "title": f"$steps.{generate_step.step_id}.result.title",
                    "question_type": f"$steps.{generate_step.step_id}.result.question_type",
                    "questions": f"$steps.{generate_step.step_id}.result.questions",
                    "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
                },
                depends_on=[generate_step.step_id],
                reason="The user asked to add the generated quiz to a folder, so it must be saved first.",
            )
            completed_steps.append(save_step)

        folder_step = self._first_step_with_tool(completed_steps, "folder_get_by_name")
        if wants_folder_add and folder_step is None:
            folder_step = PlanStep(
                step_id=self._next_step_id(completed_steps),
                tool_name="folder_get_by_name",
                arguments={"name": folder_name},
                depends_on=[save_step.step_id] if save_step else [generate_step.step_id],
                reason="Resolve the target folder named by the user.",
            )
            completed_steps.append(folder_step)

        if wants_folder_add and self._first_step_with_tool(completed_steps, "folder_add_saved_quiz") is None:
            if save_step is not None and folder_step is not None:
                completed_steps.append(
                    PlanStep(
                        step_id=self._next_step_id(completed_steps),
                        tool_name="folder_add_saved_quiz",
                        arguments={
                            "folder_id": f"$steps.{folder_step.step_id}.result.folder_id",
                            "saved_quiz_id": f"$steps.{save_step.step_id}.result.saved_quiz_id",
                        },
                        depends_on=[save_step.step_id, folder_step.step_id],
                        reason="Add the saved generated quiz to the requested folder.",
                )
            )

        live_link_step = next((step for step in completed_steps if step.tool_name in LIVE_QUIZ_TOOLS), None)
        if wants_live_quiz_link and live_link_step is None:
            live_arguments: dict[str, Any] = {
                "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
            }
            if requested_duration is not None:
                live_arguments["duration"] = requested_duration
            live_link_step = PlanStep(
                step_id=self._next_step_id(completed_steps),
                tool_name="live_quiz_ensure_access_link",
                arguments=live_arguments,
                depends_on=[generate_step.step_id],
                reason="Ensure the generated quiz has an active live quiz link.",
            )
            completed_steps.append(live_link_step)

        if (
            wants_live_quiz_link
            and recipient_emails
            and self._first_step_with_tool(completed_steps, "live_quiz_send_invites") is None
            and live_link_step is not None
        ):
            completed_steps.append(
                PlanStep(
                    step_id=self._next_step_id(completed_steps),
                    tool_name="live_quiz_send_invites",
                    arguments={
                        "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
                        "recipient_emails": recipient_emails,
                        "live_quiz_link": f"$steps.{live_link_step.step_id}.result.live_quiz_link",
                    },
                    requires_confirmation=True,
                    depends_on=[generate_step.step_id, live_link_step.step_id],
                    reason="Send the generated quiz live link to the requested recipients.",
                )
            )

        if wants_download and self._first_step_with_tool(completed_steps, "quiz_export_link") is None:
            export_arguments = {
                "quiz_id": f"$steps.{generate_step.step_id}.result.quiz_id",
            }
            if requested_format:
                export_arguments["format"] = requested_format
            completed_steps.append(
                PlanStep(
                    step_id=self._next_step_id(completed_steps),
                    tool_name="quiz_export_link",
                    arguments=export_arguments,
                    depends_on=[generate_step.step_id],
                    reason="Prepare the requested download for the generated quiz.",
                )
            )

        return completed_steps

    def _first_step_with_tool(self, steps: list[PlanStep], tool_name: str) -> PlanStep | None:
        return next((step for step in steps if step.tool_name == tool_name), None)

    def _next_step_id(self, steps: list[PlanStep]) -> str:
        existing_ids = {step.step_id for step in steps}
        index = len(existing_ids) + 1
        while f"step_{index}" in existing_ids:
            index += 1
        return f"step_{index}"

    def _folder_name_from_message(self, message: str) -> str | None:
        match = FOLDER_NAME_PATTERN.search(message)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _explicit_export_format_from_message(self, message: str) -> str | None:
        for pattern, file_format in EXPORT_FORMAT_PATTERNS:
            if pattern.search(message):
                return file_format
        return None

    def _email_addresses_from_message(self, message: str) -> list[str]:
        seen: set[str] = set()
        emails: list[str] = []
        for match in EMAIL_ADDRESS_PATTERN.finditer(message):
            email = match.group(0).lower()
            if email not in seen:
                seen.add(email)
                emails.append(email)
        return emails

    def _normalize_live_quiz_duration(self, steps: list[PlanStep], message: str) -> list[PlanStep]:
        duration = self._explicit_live_quiz_duration_from_message(message)
        for step in steps:
            if step.tool_name in {"live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
                if duration is not None:
                    step.arguments["duration"] = duration
                elif step.tool_name == "live_quiz_create_access_link":
                    step.arguments.pop("duration", None)
        return steps

    def _message_explicitly_supplies_live_quiz_duration(self, message: str) -> bool:
        return self._explicit_live_quiz_duration_from_message(message) is not None

    def _explicit_live_quiz_duration_from_message(self, message: str) -> int | None:
        for pattern in LIVE_QUIZ_DURATION_VALUE_PATTERNS:
            match = pattern.search(message)
            if not match:
                continue
            value = int(match.group(1))
            unit = (match.group(2) or "minutes").lower()
            if unit.startswith(("hour", "hr")):
                return value * 60
            return value
        return None

    def _normalize_live_quiz_identity(
        self,
        steps: list[PlanStep],
        message: str,
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> list[PlanStep]:
        live_steps = [step for step in steps if step.tool_name in LIVE_QUIZ_TOOLS]
        if not live_steps:
            return steps
        if any(
            step.tool_name == "live_quiz_create_access_link"
            and not self._has_generation_argument(step.arguments.get("duration"))
            for step in live_steps
        ):
            return steps
        if all(
            self._is_resolved_quiz_reference(
                step.arguments.get("quiz_id"),
                page_context=page_context,
                recent_artifacts=recent_artifacts,
            )
            for step in live_steps
        ):
            return steps

        existing_lookup = self._first_step_with_tool(steps, "library_find_saved_quiz_by_title")
        if existing_lookup is not None:
            lookup_step = existing_lookup
        else:
            title = self._live_quiz_title_from_steps_or_message(live_steps, message)
            if not title:
                return steps
            lookup_step = PlanStep(
                step_id=self._next_step_id(steps),
                tool_name="library_find_saved_quiz_by_title",
                arguments={"title": title},
                reason="Resolve the named quiz to its canonical quiz id before managing live quiz links.",
            )
            steps = self._insert_before_first_live_quiz_step(steps, lookup_step)

        for step in steps:
            if step.tool_name not in LIVE_QUIZ_TOOLS:
                continue
            quiz_id = step.arguments.get("quiz_id")
            if self._is_resolved_quiz_reference(
                quiz_id,
                page_context=page_context,
                recent_artifacts=recent_artifacts,
            ):
                continue
            step.arguments["quiz_id"] = f"$steps.{lookup_step.step_id}.result.quiz_id"
            if lookup_step.step_id not in step.depends_on:
                step.depends_on = [*step.depends_on, lookup_step.step_id]

        return steps

    def _insert_before_first_live_quiz_step(self, steps: list[PlanStep], lookup_step: PlanStep) -> list[PlanStep]:
        for index, step in enumerate(steps):
            if step.tool_name in LIVE_QUIZ_TOOLS:
                return [*steps[:index], lookup_step, *steps[index:]]
        return [*steps, lookup_step]

    def _live_quiz_title_from_steps_or_message(self, live_steps: list[PlanStep], message: str) -> str | None:
        for step in live_steps:
            quiz_id = step.arguments.get("quiz_id")
            if isinstance(quiz_id, str) and quiz_id.strip() and not self._is_resolved_quiz_reference(quiz_id):
                title = self._clean_quiz_title_candidate(quiz_id)
                if title:
                    return title
            for key in ("title", "quiz_title", "name"):
                value = step.arguments.get(key)
                if isinstance(value, str):
                    title = self._clean_quiz_title_candidate(value)
                    if title:
                        return title

        patterns = (
            r"\bquiz\s+(?:on|about|named|called|titled)\s+(.+?)(?:\s+(?:currently|already|have|has|with|for|to|and)\b|[?.!,]|$)",
            r"\b(?:live\s+quiz\s+link|live\s+link|access\s+link|attempt\s+link|participant\s+link)\s+(?:for|on)\s+(.+?)(?:[?.!,]|$)",
            r"\b(?:for|on)\s+(?:my\s+|the\s+)?(.+?)\s+quiz\b",
        )
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                title = self._clean_quiz_title_candidate(match.group(1))
                if title:
                    return title
        return None

    def _clean_quiz_title_candidate(self, value: str) -> str | None:
        candidate = re.sub(r"\s+", " ", value).strip(" .?!,;:'\"")
        if not candidate:
            return None
        generic_values = {
            "quiz",
            "the quiz",
            "this quiz",
            "that quiz",
            "it",
            "the one",
            "the above",
            "the quiz above",
        }
        if candidate.lower() in generic_values:
            return None
        return candidate

    def _is_resolved_quiz_reference(
        self,
        value: Any,
        *,
        page_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
    ) -> bool:
        if not isinstance(value, str):
            return self._has_generation_argument(value)
        stripped = value.strip()
        if not stripped:
            return False
        if stripped.startswith("$steps.") or stripped.startswith("$context."):
            return True
        if CANONICAL_ID_PATTERN.fullmatch(stripped):
            return True
        if page_context and self._title_from_mapping_for_quiz_id(page_context, stripped):
            return True
        for artifact in recent_artifacts or []:
            if self._title_from_mapping_for_quiz_id(artifact, stripped):
                return True
        return False

    async def _repair_step_arguments(
        self,
        *,
        step: PlanStep,
        message: str,
        page_context: dict[str, Any] | None,
        previous_results: list[dict[str, Any]],
    ) -> ExecutorDecision:
        return await self.model_router.execute(
            build_executor_prompt(
                message=message,
                planned_tool_name=step.tool_name,
                step_id=step.step_id,
                current_arguments=step.arguments,
                previous_results=previous_results,
                page_context=page_context,
            )
        )

    async def _preflight_step(
        self,
        *,
        step: PlanStep,
        arguments: dict[str, Any],
        run: AssistantRun,
        conversation_id: str,
        user: UserOut | None,
    ) -> AssistantChatResponse | None:
        dependency_issue = self._dependency_issue_for_step(step, arguments, run)
        if dependency_issue is not None:
            return await self._handle_dependency_issue(
                step=step,
                arguments=arguments,
                run=run,
                conversation_id=conversation_id,
                dependency_issue=dependency_issue,
                user=user,
            )

        if step.tool_name == "quiz_generate" and self._message_explicitly_requests_generation(run.user_message):
            missing_generation_arguments = self._missing_generation_fields(
                arguments=arguments,
                user_message=run.user_message,
            )
            if missing_generation_arguments:
                step.arguments = arguments
                await self.pending_run_store.save(
                    self._pending_run_snapshot(
                        run,
                        conversation_id=conversation_id,
                        current_step_index=run.current_step_index,
                        pending_mode="missing_arguments",
                        missing_arguments=missing_generation_arguments,
                    )
                )
                return AssistantChatResponse(
                    message=self._missing_tool_argument_message(step.tool_name, missing_generation_arguments),
                    conversation_id=conversation_id,
                    artifacts=[],
                )

        missing_arguments = self._missing_required_tool_arguments(step.tool_name, arguments)
        if not missing_arguments:
            choice_response = await self._choice_action_response(
                step=step,
                arguments=arguments,
                run=run,
                conversation_id=conversation_id,
                user=user,
            )
            if choice_response is not None:
                return choice_response
            return None
        step.arguments = arguments
        await self.pending_run_store.save(
            self._pending_run_snapshot(
                run,
                conversation_id=conversation_id,
                current_step_index=run.current_step_index,
                pending_mode="missing_arguments",
                missing_arguments=missing_arguments,
            )
        )
        return AssistantChatResponse(
            message=self._missing_tool_argument_message(step.tool_name, missing_arguments),
            conversation_id=conversation_id,
            artifacts=[],
        )

    async def _choice_action_response(
        self,
        *,
        step: PlanStep,
        arguments: dict[str, Any],
        run: AssistantRun,
        conversation_id: str,
        user: UserOut | None,
    ) -> AssistantChatResponse | None:
        selectable_arguments = SELECTABLE_TOOL_ARGUMENTS.get(step.tool_name, {})
        for argument_name, config in selectable_arguments.items():
            if self._has_generation_argument(arguments.get(argument_name)):
                continue

            actions = [
                AssistantAction(
                    type="choice",
                    label=str(choice["label"]),
                    run_id=run.run_id,
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    arguments={**arguments, argument_name: choice["value"]},
                )
                for choice in config["choices"]
            ]
            step.arguments = arguments
            await self.pending_run_store.save(
                self._pending_run_snapshot(run, conversation_id=conversation_id)
            )
            return AssistantChatResponse(
                message=str(config["message"]),
                conversation_id=conversation_id,
                actions=actions,
                artifacts=[],
            )

        return None

    def _dependency_issue_for_step(
        self,
        step: PlanStep,
        arguments: dict[str, Any],
        run: AssistantRun,
    ) -> dict[str, Any] | None:
        if step.tool_name in LIVE_QUIZ_TOOLS:
            for result in run.tool_results:
                if result.tool_name == "library_find_saved_quiz_by_title" and result.data.get("found") is False:
                    return {
                        "type": "missing_quiz",
                        "quiz_title": result.data.get("query") or "that quiz",
                        "result": result,
                    }

        if step.tool_name != "folder_add_saved_quiz" or self._has_generation_argument(arguments.get("folder_id")):
            return None
        for result in run.tool_results:
            if result.tool_name in {"folder_get_by_name", "folder_get"} and result.data.get("found") is False:
                return {
                    "type": "missing_folder",
                    "folder_name": result.data.get("name") or "that folder",
                    "result": result,
                }
        return None

    async def _handle_dependency_issue(
        self,
        *,
        step: PlanStep,
        arguments: dict[str, Any],
        run: AssistantRun,
        conversation_id: str,
        dependency_issue: dict[str, Any],
        user: UserOut | None,
    ) -> AssistantChatResponse:
        if dependency_issue["type"] == "missing_folder":
            folder_name = str(dependency_issue.get("folder_name") or "that folder")
            create_step = PlanStep(
                step_id=f"{step.step_id}_create_folder",
                tool_name="folder_create",
                arguments={"name": folder_name},
                requires_confirmation=True,
                reason="The requested folder does not exist yet.",
            )
            add_step = PlanStep(
                step_id=step.step_id,
                tool_name=step.tool_name,
                arguments={
                    **arguments,
                    "folder_id": f"$steps.{create_step.step_id}.result.folder_id",
                },
                requires_confirmation=step.requires_confirmation,
                depends_on=[*step.depends_on, create_step.step_id],
                reason=step.reason,
            )
            recovered_plan = [
                *run.plan[: run.current_step_index],
                create_step,
                add_step,
                *run.plan[run.current_step_index + 1 :],
            ]
            if len(recovered_plan) > settings.ASSISTANT_MAX_TOOL_CALLS:
                return AssistantChatResponse(
                    message=(
                        f"You do not have a folder named {folder_name}, and this request needs more "
                        "steps than I can safely run at once. Please ask me to create the folder first."
                    ),
                    conversation_id=conversation_id,
                    artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
                )
            run.plan = recovered_plan
            run.current_step_index = run.current_step_index
            action = AssistantAction(
                type="confirm",
                label=f"Create {folder_name} folder",
                run_id=run.run_id,
                step_id=create_step.step_id,
                tool_name=create_step.tool_name,
                arguments=create_step.arguments,
            )
            await self.pending_run_store.save(
                self._pending_run_snapshot(run, conversation_id=conversation_id)
            )
            return AssistantChatResponse(
                message=(
                    f"You do not have a folder named {folder_name}. "
                    "Confirm if you want me to create it and continue adding the quiz."
                ),
                conversation_id=conversation_id,
                actions=[action],
                artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
            )

        if dependency_issue["type"] == "missing_quiz":
            quiz_title = str(dependency_issue.get("quiz_title") or "that quiz")
            return AssistantChatResponse(
                message=f"I could not find a saved quiz named {quiz_title}.",
                conversation_id=conversation_id,
                artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
            )

        return AssistantChatResponse(
            message="I could not continue because a required earlier lookup did not return a usable result.",
            conversation_id=conversation_id,
            artifacts=self._infer_artifacts_from_results(run.tool_results, suppress_internal_lookup=True),
        )

    def _missing_required_tool_arguments(self, tool_name: str, arguments: dict[str, Any]) -> list[str]:
        return [
            argument_name
            for argument_name in REQUIRED_TOOL_ARGUMENTS.get(tool_name, ())
            if not self._has_generation_argument(arguments.get(argument_name))
        ]

    def _missing_tool_argument_message(self, tool_name: str, missing_arguments: list[str]) -> str:
        readable = {
            "folder_id": "folder",
            "saved_quiz_id": "saved quiz",
            "quiz_id": "quiz",
            "title": "title",
            "questions": "questions",
            "question_type": "question type",
            "name": "name",
            "duration": "duration",
            "num_questions": "number of questions",
            "profession": "topic or profession",
        }
        missing = ", ".join(readable.get(argument, argument) for argument in missing_arguments)
        if tool_name == "quiz_generate":
            return f"I need the {missing} before generating a quiz."
        if tool_name == "folder_add_saved_quiz":
            return f"I need the {missing} before I can add the quiz to a folder."
        if tool_name == "library_save_quiz":
            return f"I need the {missing} before I can save the quiz."
        if tool_name == "live_quiz_create_access_link":
            return f"I need the live quiz {missing} before I can create the link."
        return f"I need the {missing} before I can continue."

    def _arguments_from_user_message_for_missing_fields(
        self,
        *,
        tool_name: str,
        missing_arguments: list[str],
        message: str,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {}
        if tool_name == "quiz_generate":
            if "question_type" in missing_arguments:
                question_type = self._question_type_from_message(message)
                if question_type is not None:
                    arguments["question_type"] = question_type
            if "num_questions" in missing_arguments:
                num_questions = self._num_questions_from_message(message)
                if num_questions is not None:
                    arguments["num_questions"] = num_questions
            if "profession" in missing_arguments:
                profession = self._profession_from_follow_up_message(message)
                if profession is not None:
                    arguments["profession"] = profession
        if tool_name in {"live_quiz_create_access_link", "live_quiz_ensure_access_link"} and "duration" in missing_arguments:
            duration = self._explicit_live_quiz_duration_from_message(message)
            if duration is not None:
                arguments["duration"] = duration
        if tool_name in {"share_send_email"} and "recipient_email" in missing_arguments:
            emails = self._email_addresses_from_message(message)
            if emails:
                arguments["recipient_email"] = emails[0]
        if tool_name in {"live_quiz_send_invites"} and "recipient_emails" in missing_arguments:
            emails = self._email_addresses_from_message(message)
            if emails:
                arguments["recipient_emails"] = emails
        if tool_name in {"folder_get_by_name", "folder_create"} and "name" in missing_arguments:
            folder_name = self._folder_name_from_message(message)
            if folder_name is not None:
                arguments["name"] = folder_name
        return arguments

    def _first_unexecuted_step_index(self, run: AssistantRun) -> int:
        completed_step_ids = {result.step_id for result in run.tool_results if result.ok}
        for index, step in enumerate(run.plan):
            if step.step_id not in completed_step_ids:
                return index
        return len(run.plan)

    def _resolve_arguments(
        self,
        value: Any,
        *,
        run: AssistantRun,
        user: UserOut | None,
    ) -> Any:
        if isinstance(value, dict):
            return {
                key: self._resolve_arguments(item, run=run, user=user)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._resolve_arguments(item, run=run, user=user) for item in value]
        if not isinstance(value, str):
            return value

        step_match = PLACEHOLDER_PATTERN.match(value)
        if step_match:
            step_id, field_name = step_match.groups()
            for result in run.tool_results:
                if result.step_id == step_id:
                    return result.data.get(field_name, value)
            return value

        context_match = CONTEXT_PATTERN.match(value)
        if context_match:
            field_name = context_match.group(1)
            if field_name == "user_id" and user is not None:
                return str(user.id)
            return value

        return value

    def _needs_executor_repair(self, value: Any) -> bool:
        if isinstance(value, dict):
            return any(self._needs_executor_repair(item) for item in value.values())
        if isinstance(value, list):
            return any(self._needs_executor_repair(item) for item in value)
        return isinstance(value, str) and value.startswith("$")

    def _merge_selectable_arguments(
        self,
        *,
        tool_name: str,
        planned_arguments: dict[str, Any],
        submitted_arguments: dict[str, Any],
    ) -> dict[str, Any]:
        merged_arguments = dict(planned_arguments)
        selectable_arguments = SELECTABLE_TOOL_ARGUMENTS.get(tool_name, {})
        for argument_name, config in selectable_arguments.items():
            submitted_value = submitted_arguments.get(argument_name)
            allowed_values = {choice["value"] for choice in config["choices"]}
            if submitted_value in allowed_values:
                merged_arguments[argument_name] = submitted_value
        return merged_arguments

    def _blocked_tool_call_message(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        user_message: str,
    ) -> str | None:
        if tool_name != "quiz_generate":
            return None

        if not self._message_explicitly_requests_generation(user_message):
            return (
                "I will not generate a new quiz unless you explicitly ask for one. "
                "If you want to work with an existing quiz, tell me which quiz and action."
            )

        missing_fields = self._missing_generation_fields(
            arguments=arguments,
            user_message=user_message,
        )
        if missing_fields:
            readable = {
                "profession": "topic or profession",
                "question_type": "question type",
                "num_questions": "number of questions",
            }
            missing = ", ".join(readable.get(field, field) for field in dict.fromkeys(missing_fields))
            return f"I need the {missing} before generating a quiz."

        return None

    def _message_explicitly_requests_generation(self, message: str) -> bool:
        if self._verb_before_quiz_content_request(message):
            return True
        if LIVE_QUIZ_LINK_ONLY_CREATION_PATTERN.search(message):
            return False
        return bool(GENERATION_INTENT_PATTERN.search(message) and not LIVE_QUIZ_LINK_INTENT_PATTERN.search(message))

    def _verb_before_quiz_content_request(self, message: str) -> bool:
        verb_pattern = re.compile(rf"\b{GENERATION_VERBS_PATTERN}\b", re.IGNORECASE)
        quiz_pattern = re.compile(rf"\b{QUIZ_NOUN_PATTERN}\b", re.IGNORECASE)
        link_terms = re.compile(r"\b(link|access|invite|attempt|participant|code)\b", re.IGNORECASE)
        content_cues = re.compile(r"^\s*(?:on|about|for|with|covering|regarding)\b|[,.;!?]", re.IGNORECASE)

        for verb_match in verb_pattern.finditer(message):
            suffix = message[verb_match.end() : verb_match.end() + 180]
            quiz_match = quiz_pattern.search(suffix)
            if quiz_match is None:
                continue
            between_verb_and_quiz = suffix[: quiz_match.start()]
            after_quiz = suffix[quiz_match.end() : quiz_match.end() + 60]
            if link_terms.search(between_verb_and_quiz):
                continue
            if link_terms.match(after_quiz.strip()):
                continue
            if content_cues.search(after_quiz):
                return True
        return False

    def _missing_generation_fields(self, *, arguments: dict[str, Any], user_message: str) -> list[str]:
        missing_fields = [
            field_name
            for field_name in QUIZ_GENERATE_REQUIRED_FIELDS
            if not self._has_generation_argument(arguments.get(field_name))
        ]
        question_type = arguments.get("question_type")
        if self._has_generation_argument(question_type) and not self._is_valid_question_type(question_type):
            missing_fields.append("question_type")
        missing_fields.extend(self._missing_generation_details_from_user_message(user_message))
        num_questions = arguments.get("num_questions")
        if self._has_generation_argument(num_questions):
            try:
                parsed_num_questions = int(num_questions)
            except (TypeError, ValueError):
                missing_fields.append("num_questions")
            else:
                if parsed_num_questions <= 0:
                    missing_fields.append("num_questions")
        return list(dict.fromkeys(missing_fields))

    def _is_valid_question_type(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return value.strip().lower() in {"multichoice", "true-false", "short-answer", "open-ended"}

    def _missing_generation_details_from_user_message(self, message: str) -> list[str]:
        missing: list[str] = []
        if not re.search(
            r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\b",
            message,
            re.IGNORECASE,
        ):
            missing.append("num_questions")
        if not any(pattern.search(message) for pattern, _question_type in QUESTION_TYPE_PATTERNS):
            missing.append("question_type")
        return missing

    def _question_type_from_message(self, message: str) -> str | None:
        normalized = self._canonical_question_type_from_text(message)
        if normalized is not None:
            return normalized
        return None

    def _canonical_question_type_from_text(self, text: str) -> str | None:
        for pattern, question_type in QUESTION_TYPE_PATTERNS:
            if pattern.search(text):
                return question_type
        return None

    def _num_questions_from_message(self, message: str) -> int | None:
        digit_match = re.search(r"\b(\d{1,2})\b", message)
        if digit_match:
            value = int(digit_match.group(1))
            return value if value > 0 else None
        word_match = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b",
            message,
            re.IGNORECASE,
        )
        if word_match:
            return NUMBER_WORDS[word_match.group(1).lower()]
        return None

    def _profession_from_follow_up_message(self, message: str) -> str | None:
        patterns = (
            r"\b(?:topic|subject|profession|context)\s+(?:is|should\s+be|=)\s+(.+)$",
            r"\b(?:on|about|for)\s+(.+)$",
        )
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .?!,;:'\"")
                if candidate:
                    return candidate
        candidate = re.sub(r"\s+", " ", message).strip(" .?!,;:'\"")
        if 2 <= len(candidate) <= 120:
            return candidate
        return None

    def _has_generation_argument(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return bool(value)
        return True

    def _tool_error_message(self, result: ToolResult) -> str:
        error = (
            result.data.get("error")
            or result.data.get("message")
            or result.data.get("detail")
            or result.data.get("result")
            or "The tool returned an error."
        )
        if isinstance(error, list):
            error = "; ".join(str(item) for item in error)
        if result.tool_name == "quiz_generate":
            return f"I could not generate the quiz: {error}"
        return f"I could not complete `{result.tool_name}`: {error}"

    def _normalize_tool_result(
        self,
        *,
        step_id: str,
        tool_name: str,
        raw_result: Any,
    ) -> ToolResult:
        data = raw_result if isinstance(raw_result, dict) else {"result": raw_result}
        normalized = dict(data)

        if "id" in normalized:
            if tool_name == "folder_create":
                normalized.setdefault("folder_id", normalized["id"])
            if tool_name == "library_save_quiz":
                normalized.setdefault("saved_quiz_id", normalized["id"])
            if tool_name == "folder_add_saved_quiz":
                normalized.setdefault("folder_item_id", normalized["id"])

        questions = normalized.get("questions")
        if isinstance(questions, list):
            normalized.setdefault("question_count", len(questions))

        is_error = bool(normalized.get("isError") or normalized.get("error"))
        if tool_name == "quiz_generate" and not normalized.get("questions"):
            normalized.setdefault("error", "Quiz generation returned no questions.")
            is_error = True

        return ToolResult(
            ok=not is_error,
            step_id=step_id,
            tool_name=tool_name,
            data=normalized,
        )

    async def _compose_final_response(self, message: str, run: AssistantRun) -> AssistantFinalResponse:
        return await self.model_router.final_response(
            build_final_response_prompt(
                message=message,
                run_results=self._dump_results(run),
            )
        )

    def _deterministic_final_response(self, run: AssistantRun) -> AssistantFinalResponse | None:
        return self._deterministic_final_response_for_results(run.tool_results)

    def _deterministic_final_response_for_results(
        self,
        results: list[ToolResult],
    ) -> AssistantFinalResponse | None:
        if not results:
            return None
        last = results[-1]
        data = last.data
        tool_names = [result.tool_name for result in results]

        if "quiz_export_link" in tool_names and "share_send_email" in tool_names:
            email_result = next(
                (result for result in reversed(results) if result.tool_name == "share_send_email"),
                None,
            )
            export_result = next(
                (result for result in reversed(results) if result.tool_name == "quiz_export_link"),
                None,
            )
            recipient_email = (email_result.data.get("recipient_email") if email_result else None) or "the recipient"
            file_format = str((export_result.data.get("format") if export_result else None) or "file").upper()
            download_instruction = self._download_instruction(export_result)
            return AssistantFinalResponse(
                message=(
                    f"I prepared the {file_format} download and sent the share link to {recipient_email}. "
                    f"{download_instruction}"
                ),
            )

        if "quiz_generate" in tool_names and "live_quiz_send_invites" in tool_names:
            generate_result = next(
                (result for result in reversed(results) if result.tool_name == "quiz_generate"),
                None,
            )
            invite_result = next(
                (result for result in reversed(results) if result.tool_name == "live_quiz_send_invites"),
                None,
            )
            folder_result = next(
                (result for result in reversed(results) if result.tool_name == "folder_add_saved_quiz"),
                None,
            )
            title = (
                (folder_result.data.get("title") if folder_result else None)
                or (generate_result.data.get("title") if generate_result else None)
                or "the quiz"
            )
            sent_count = (invite_result.data.get("sent_count") if invite_result else None) or 0
            if folder_result is not None:
                folder_name = folder_result.data.get("folder_name") or "the folder"
                return AssistantFinalResponse(
                    message=(
                        f"I generated {title}, saved it, added it to {folder_name}, and sent live quiz "
                        f"invite{'s' if sent_count != 1 else ''} to {sent_count} recipient{'s' if sent_count != 1 else ''}."
                    )
                )
            return AssistantFinalResponse(
                message=(
                    f"I generated {title} and sent live quiz invite{'s' if sent_count != 1 else ''} "
                    f"to {sent_count} recipient{'s' if sent_count != 1 else ''}."
                )
            )

        if "folder_move_quiz" in tool_names and "folder_delete" in tool_names:
            move_result = next(
                (result for result in reversed(results) if result.tool_name == "folder_move_quiz"),
                None,
            )
            delete_result = next(
                (result for result in reversed(results) if result.tool_name == "folder_delete"),
                None,
            )
            title = (move_result.data.get("title") if move_result else None) or "the quiz"
            target_folder = (move_result.data.get("target_folder_name") if move_result else None) or "the target folder"
            deleted_folder = (delete_result.data.get("folder_name") if delete_result else None) or "the source folder"
            return AssistantFinalResponse(
                message=f"I moved {title} to {target_folder} and deleted {deleted_folder} folder.",
            )

        if "quiz_generate" in tool_names and "library_save_quiz" in tool_names and "folder_add_saved_quiz" in tool_names:
            folder_add_result = next(
                (result for result in reversed(results) if result.tool_name == "folder_add_saved_quiz"),
                None,
            )
            title = (folder_add_result.data.get("title") if folder_add_result else None) or "the quiz"
            folder_name = (folder_add_result.data.get("folder_name") if folder_add_result else None) or "the folder"
            if "quiz_export_link" in tool_names:
                export_result = next(
                    (result for result in reversed(results) if result.tool_name == "quiz_export_link"),
                    None,
                )
                file_format = str((export_result.data.get("format") if export_result else None) or "file").upper()
                return AssistantFinalResponse(
                    message=(
                        f"I generated {title}, saved it, added it to {folder_name}, and prepared the "
                        f"{file_format} download. {self._download_instruction(export_result)}"
                    )
                )
            return AssistantFinalResponse(message=f"I generated, saved, and added {title} to {folder_name}.")

        if "quiz_generate" in tool_names and "library_save_quiz" in tool_names:
            if "quiz_export_link" in tool_names:
                export_result = next(
                    (result for result in reversed(results) if result.tool_name == "quiz_export_link"),
                    None,
                )
                file_format = str((export_result.data.get("format") if export_result else None) or "file").upper()
                return AssistantFinalResponse(
                    message=f"I generated, saved, and prepared the {file_format} download. {self._download_instruction(export_result)}"
                )
            return AssistantFinalResponse(message="I generated and saved the quiz.")

        if last.tool_name == "library_list_saved_quizzes":
            items = data.get("result") if "result" in data else data
            count = len(items) if isinstance(items, list) else 0
            return AssistantFinalResponse(
                message=f"You have {count} saved {'quiz' if count == 1 else 'quizzes'}.",
            )

        if last.tool_name == "library_list_history":
            items = data.get("result") if "result" in data else data
            count = len(items) if isinstance(items, list) else 0
            return AssistantFinalResponse(
                message=f"I found {count} quiz history item{'s' if count != 1 else ''}.",
            )

        if last.tool_name == "folder_list":
            items = data.get("result") if "result" in data else data
            count = len(items) if isinstance(items, list) else 0
            return AssistantFinalResponse(
                message=f"I found {count} folder{'s' if count != 1 else ''}.",
            )

        if last.tool_name == "folder_get_by_name":
            folder_name = data.get("name") or "that folder"
            if data.get("found") is False:
                return AssistantFinalResponse(message=f"You do not have a folder named {folder_name}.")
            quizzes = data.get("quizzes")
            count = len(quizzes) if isinstance(quizzes, list) else 0
            return AssistantFinalResponse(
                message=f"I found {count} {'quiz' if count == 1 else 'quizzes'} in {folder_name} Folder.",
            )

        if last.tool_name == "folder_find_quiz_by_title":
            query = data.get("query") or "that quiz"
            matches = data.get("matches")
            count = len(matches) if isinstance(matches, list) else 0
            if count:
                folder_names = sorted(
                    {
                        str(item.get("folder_name"))
                        for item in matches
                        if isinstance(item, dict) and item.get("folder_name")
                    }
                )
                if len(folder_names) == 1:
                    location = f"{folder_names[0]} Folder"
                elif folder_names:
                    location = f"{', '.join(folder_names)} Folders"
                else:
                    location = "your folder library"
                return AssistantFinalResponse(message=f"{query} is in {location}.")
            return AssistantFinalResponse(message=f"I could not find {query} in your folders.")

        if last.tool_name == "quiz_generate":
            title = data.get("title") or "quiz"
            return AssistantFinalResponse(message=f"I generated {title}.")

        if last.tool_name == "library_save_quiz":
            title = data.get("title") or "the quiz"
            return AssistantFinalResponse(message=f"I saved {title}.")

        if last.tool_name == "saved_quiz_rename":
            title = data.get("title") or "the saved quiz"
            return AssistantFinalResponse(message=f"I renamed the saved quiz to {title}.")

        if last.tool_name == "saved_quiz_delete":
            return AssistantFinalResponse(message="I deleted the saved quiz.")

        if last.tool_name == "folder_add_saved_quiz":
            title = data.get("title") or "the quiz"
            folder_name = data.get("folder_name") or "the folder"
            return AssistantFinalResponse(message=f"I added {title} to {folder_name}.")

        if last.tool_name == "folder_rename":
            name = data.get("name") or "the folder"
            return AssistantFinalResponse(message=f"I renamed the folder to {name}.")

        if last.tool_name == "folder_delete":
            folder_name = data.get("folder_name") or "the folder"
            return AssistantFinalResponse(message=f"I deleted {folder_name} folder.")

        if last.tool_name == "folder_remove_quiz":
            title = data.get("title") or "the quiz"
            folder_name = data.get("folder_name") or "the folder"
            return AssistantFinalResponse(message=f"I removed {title} from {folder_name}.")

        if last.tool_name == "folder_move_quiz":
            title = data.get("title") or "the quiz"
            target_folder = data.get("target_folder_name") or "the target folder"
            return AssistantFinalResponse(message=f"I moved {title} to {target_folder}.")

        if last.tool_name == "share_create_link":
            return AssistantFinalResponse(message="I created the share link.")

        if last.tool_name == "share_send_email":
            recipient_email = data.get("recipient_email") or "the recipient"
            return AssistantFinalResponse(message=f"I sent the quiz link to {recipient_email}.")

        if last.tool_name == "quiz_export_link":
            file_format = str(data.get("format") or "file").upper()
            return AssistantFinalResponse(
                message=f"I prepared the {file_format} export. {self._download_instruction(last)}"
            )

        if last.tool_name == "live_quiz_get_access_link":
            if data.get("found") is False:
                return AssistantFinalResponse(message="This quiz does not have an active live quiz link yet.")
            title = data.get("title") or "this quiz"
            return AssistantFinalResponse(message=f"I found an active live quiz link for {title}.")

        if last.tool_name in {"live_quiz_create_access_link", "live_quiz_ensure_access_link"}:
            title = data.get("title") or "this quiz"
            reused = bool(data.get("reused_existing"))
            if reused:
                return AssistantFinalResponse(message=f"I found and reused the active live quiz link for {title}.")
            return AssistantFinalResponse(message=f"I created a live quiz link for {title}.")

        if last.tool_name == "live_quiz_send_invites":
            sent_count = data.get("sent_count") or 0
            failed_count = data.get("failed_count") or 0
            if failed_count:
                return AssistantFinalResponse(
                    message=f"Sent quiz invite{'s' if sent_count != 1 else ''} to {sent_count} recipient{'s' if sent_count != 1 else ''}; {failed_count} failed."
                )
            return AssistantFinalResponse(
                message=f"Sent quiz invite{'s' if sent_count != 1 else ''} to {sent_count} recipient{'s' if sent_count != 1 else ''}."
            )

        if last.tool_name == "notification_list":
            items = data.get("items") if isinstance(data, dict) else []
            count = len(items) if isinstance(items, list) else 0
            unread_count = data.get("unread_count") if isinstance(data, dict) else None
            if isinstance(unread_count, int):
                return AssistantFinalResponse(
                    message=f"I found {count} notification{'s' if count != 1 else ''}; {unread_count} unread.",
                )
            return AssistantFinalResponse(message=f"I found {count} notification{'s' if count != 1 else ''}.")

        if last.tool_name == "notification_mark_read":
            return AssistantFinalResponse(message="I marked the notification as read.")

        if last.tool_name == "notification_delete":
            return AssistantFinalResponse(message="I deleted the notification.")

        return None

    def _dump_results(self, run: AssistantRun) -> list[dict[str, Any]]:
        return [result.model_dump(mode="json") for result in run.tool_results]

    def _confirmation_label(self, tool_name: str) -> str:
        labels = {
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
        }
        return labels.get(tool_name, "Confirm action")

    def _confirmation_message(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        run: AssistantRun,
    ) -> str:
        if tool_name == "folder_move_quiz":
            title = self._folder_item_title_from_results(str(arguments.get("folder_item_id") or ""), run)
            source = self._folder_name_from_results(str(arguments.get("source_folder_id") or ""), run)
            target = self._folder_name_from_results(str(arguments.get("target_folder_id") or ""), run)
            return f"Please confirm: move {title} from {source} to {target}."

        if tool_name == "folder_delete":
            folder_name = self._folder_name_from_results(str(arguments.get("folder_id") or ""), run)
            return f"Please confirm: delete {folder_name} folder."

        if tool_name == "folder_remove_quiz":
            title = self._folder_item_title_from_results(str(arguments.get("folder_item_id") or ""), run)
            folder_name = self._folder_name_from_results(str(arguments.get("folder_id") or ""), run)
            return f"Please confirm: remove {title} from {folder_name}."

        if tool_name == "folder_add_saved_quiz":
            folder_name = self._folder_name_from_results(str(arguments.get("folder_id") or ""), run)
            title = self._saved_quiz_title_from_results(str(arguments.get("saved_quiz_id") or ""), run)
            return f"Please confirm: add {title} to {folder_name}."

        if tool_name == "folder_create":
            name = str(arguments.get("name") or "this folder")
            return f"Please confirm: create the {name} folder."

        if tool_name == "folder_rename":
            new_name = str(arguments.get("new_name") or "the new name")
            return f"Please confirm: rename this folder to {new_name}."

        if tool_name == "library_save_quiz":
            title = str(arguments.get("title") or "this quiz")
            return f"Please confirm: save {title} to your library."

        if tool_name == "saved_quiz_rename":
            current_title = self._saved_quiz_title_from_results(str(arguments.get("saved_quiz_id") or ""), run)
            title = str(arguments.get("title") or "the new title")
            return f"Please confirm: rename {current_title} to {title}."

        if tool_name == "saved_quiz_delete":
            return "Please confirm: delete this saved quiz."

        if tool_name == "share_create_link":
            return "Please confirm: create a share link for this quiz."

        if tool_name == "share_send_email":
            email = str(arguments.get("recipient_email") or "the recipient")
            return f"Please confirm: send this quiz link to {email}."

        if tool_name == "live_quiz_create_access_link":
            title = self._quiz_title_from_context(str(arguments.get("quiz_id") or ""), run)
            return f"Please confirm: create a live quiz link for {title}."

        if tool_name == "live_quiz_send_invites":
            recipient_emails = arguments.get("recipient_emails")
            title = self._quiz_title_from_context(str(arguments.get("quiz_id") or ""), run)
            if isinstance(recipient_emails, list):
                count = len(recipient_emails)
                if count == 1:
                    return f"Please confirm: send {title} quiz invite to {recipient_emails[0]}."
                return f"Please confirm: send {title} quiz invites to {count} recipients."
            return f"Please confirm: send {title} quiz invites."

        if tool_name == "notification_delete":
            return "Please confirm: delete this notification."

        return "Please confirm this action."

    def _download_instruction(self, export_result: ToolResult | None) -> str:
        if export_result is not None and export_result.data.get("auto_execute"):
            return "The download should start now; if it does not, use the Download quiz button below."
        return "Click the Download quiz button below to start the download."

    def _folder_name_from_results(self, folder_id: str, run: AssistantRun) -> str:
        if not folder_id:
            return "this folder"
        for result in reversed(run.tool_results):
            data = result.data
            if result.tool_name in {"folder_get", "folder_get_by_name"}:
                if folder_id in {str(data.get("id") or ""), str(data.get("folder_id") or "")}:
                    return str(data.get("name") or "this folder")
            if result.tool_name == "folder_list":
                folders = data.get("result") if isinstance(data, dict) and "result" in data else data
                if isinstance(folders, list):
                    for folder in folders:
                        if not isinstance(folder, dict):
                            continue
                        if folder_id in {str(folder.get("id") or ""), str(folder.get("folder_id") or "")}:
                            return str(folder.get("name") or "this folder")
        return "this folder"

    def _folder_item_title_from_results(self, folder_item_id: str, run: AssistantRun) -> str:
        if not folder_item_id:
            return "this quiz"
        for result in reversed(run.tool_results):
            data = result.data
            folder_quizzes = data.get("quizzes") if isinstance(data, dict) else None
            if isinstance(folder_quizzes, list):
                for item in folder_quizzes:
                    if not isinstance(item, dict):
                        continue
                    if folder_item_id in {str(item.get("id") or ""), str(item.get("folder_item_id") or "")}:
                        return str(item.get("title") or "this quiz")
            matches = data.get("matches") if isinstance(data, dict) else None
            if isinstance(matches, list):
                for item in matches:
                    if not isinstance(item, dict):
                        continue
                    if folder_item_id in {str(item.get("id") or ""), str(item.get("folder_item_id") or "")}:
                        return str(item.get("title") or "this quiz")
        return "this quiz"

    def _saved_quiz_title_from_results(self, saved_quiz_id: str, run: AssistantRun) -> str:
        if not saved_quiz_id:
            return "this saved quiz"
        for result in reversed(run.tool_results):
            data = result.data
            if result.tool_name in {"library_save_quiz", "library_get_saved_quiz", "saved_quiz_rename"}:
                if saved_quiz_id in {str(data.get("id") or ""), str(data.get("saved_quiz_id") or "")}:
                    return str(data.get("title") or "this saved quiz")
            if result.tool_name == "library_find_saved_quiz_by_title":
                if saved_quiz_id in {str(data.get("id") or ""), str(data.get("saved_quiz_id") or "")}:
                    return str(data.get("title") or "this saved quiz")
                matches = data.get("matches")
                if isinstance(matches, list):
                    for match in matches:
                        if not isinstance(match, dict):
                            continue
                        if saved_quiz_id in {str(match.get("id") or ""), str(match.get("saved_quiz_id") or "")}:
                            return str(match.get("title") or "this saved quiz")
            if result.tool_name == "library_list_saved_quizzes":
                items = data.get("result") if isinstance(data, dict) and "result" in data else data
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        if saved_quiz_id in {str(item.get("id") or ""), str(item.get("saved_quiz_id") or "")}:
                            return str(item.get("title") or "this saved quiz")
        return "this saved quiz"

    def _quiz_title_from_context(self, quiz_id: str, run: AssistantRun) -> str:
        if not quiz_id:
            return "this quiz"

        for result in reversed(run.tool_results):
            title = self._title_from_mapping_for_quiz_id(result.data, quiz_id)
            if title:
                return title

        title = self._title_from_mapping_for_quiz_id(run.page_context or {}, quiz_id)
        if title:
            return title

        for artifact in reversed(run.recent_artifacts or []):
            title = self._title_from_mapping_for_quiz_id(artifact, quiz_id)
            if title:
                return title

        return "this quiz"

    def _title_from_mapping_for_quiz_id(self, value: Any, quiz_id: str) -> str | None:
        if isinstance(value, dict):
            ids = {
                str(value.get("quiz_id") or ""),
                str(value.get("id") or ""),
                str(value.get("canonical_quiz_id") or ""),
                str(value.get("current_quiz_id") or ""),
            }
            metadata = value.get("metadata")
            if isinstance(metadata, dict):
                ids.update(
                    {
                        str(metadata.get("quiz_id") or ""),
                        str(metadata.get("id") or ""),
                        str(metadata.get("canonical_quiz_id") or ""),
                        str(metadata.get("current_quiz_id") or ""),
                    }
                )
            if quiz_id in ids:
                quiz_summary = value.get("quiz_summary")
                sources = [
                    value,
                    metadata if isinstance(metadata, dict) else {},
                    quiz_summary if isinstance(quiz_summary, dict) else {},
                ]
                for source in sources:
                    for key in ("title", "quiz_title", "name", "label"):
                        candidate = source.get(key)
                        if isinstance(candidate, str) and candidate.strip():
                            return candidate.strip()

            for child in value.values():
                title = self._title_from_mapping_for_quiz_id(child, quiz_id)
                if title:
                    return title

        if isinstance(value, list):
            for item in value:
                title = self._title_from_mapping_for_quiz_id(item, quiz_id)
                if title:
                    return title

        return None

    def _infer_artifacts_from_results(
        self,
        results: list[ToolResult],
        *,
        suppress_internal_lookup: bool = False,
        suppress_final_status_tools: set[str] | None = None,
    ) -> list[AssistantArtifact]:
        return infer_artifacts_from_results(
            results,
            suppress_internal_lookup=suppress_internal_lookup,
            suppress_final_status_tools=suppress_final_status_tools,
        )

    def _merge_artifacts(
        self,
        model_artifacts: list[AssistantArtifact],
        deterministic_artifacts: list[AssistantArtifact],
    ) -> list[AssistantArtifact]:
        _ = model_artifacts
        return deterministic_artifacts
