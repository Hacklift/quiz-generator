from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from server.app.assistant.artifacts import infer_artifacts_from_results
from server.app.assistant.error_mapper import tool_error_message
from server.app.assistant.mcp_client import AssistantMcpClient
from server.app.assistant.model_router import AssistantModelRouter
from server.app.assistant.plan_compiler import AssistantPlanCompiler
from server.app.assistant.argument_preparation import PreparationStatus, StepPreparationPipeline
from server.app.assistant.response_presenter import AssistantResponsePresenter
from server.app.assistant.confirmation_presenter import ConfirmationPresenter
from server.app.assistant.workflow_engine import AssistantWorkflowEngine, normalize_tool_result
from server.app.assistant.prompts import (
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
    PlanStep,
    PlannerDecision,
    ToolResult,
)
from server.app.assistant.tool_policy import enforce_tool_policy, get_tool_definition
from server.app.core.config import settings
from server.app.users.models import UserOut


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
DOWNLOAD_INTENT_PATTERN = re.compile(r"\b(download|export)\b", re.IGNORECASE)
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
FOLDER_ADD_INTENT_PATTERN = re.compile(
    r"\b(add|save|put|place|move)\b.*\bfolder\b|\bfolder\b.*\b(add|save|put|place|move)\b",
    re.IGNORECASE,
)
LIVE_QUIZ_TOOLS = {
    "live_quiz_get_access_link",
    "live_quiz_create_access_link",
    "live_quiz_ensure_access_link",
    "live_quiz_send_invites",
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
        self.plan_compiler = AssistantPlanCompiler()
        self.step_preparation = StepPreparationPipeline()
        self.response_presenter = AssistantResponsePresenter()
        self.confirmation_presenter = ConfirmationPresenter()
        self.workflow_engine = AssistantWorkflowEngine(
            model_router=model_router,
            mcp_client=mcp_client,
            pending_run_store=self.pending_run_store,
            preparation=self.step_preparation,
            confirmations=self.confirmation_presenter,
            responses=self.response_presenter,
        )

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

        unresolved_intents = self.plan_compiler.missing_explicit_workflow_intents(planner.steps, message)
        if unresolved_intents:
            return AssistantChatResponse(
                message=self.plan_compiler.plan_clarification_message(unresolved_intents),
                conversation_id=conversation_id,
                artifacts=[],
            )

        self._validate_plan(planner)
        run.plan = planner.steps[: settings.ASSISTANT_MAX_TOOL_CALLS]
        run.status = "executing"

        return await self._execute_run_from_current_step(
            run=run,
            conversation_id=conversation_id,
            user=user,
            authorization_header=authorization_header,
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
        normalized = normalize_tool_result(step_id or "confirmed_step", tool_name, tool_result)
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
        pending_preparation = self.step_preparation.prepare(
            tool_name=step.tool_name,
            arguments=step.arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        missing_arguments = pending_run.missing_arguments or pending_preparation.missing_fields
        supplied_arguments = self._arguments_from_user_message_for_missing_fields(
            tool_name=step.tool_name,
            missing_arguments=missing_arguments,
            message=message,
        )
        if supplied_arguments:
            step.arguments = {**step.arguments, **supplied_arguments}
            run.user_message = f"{run.user_message}\nFollow-up details: {message}"
        elif self._should_replan_missing_argument_follow_up(
            tool_name=step.tool_name,
            missing_arguments=missing_arguments,
            message=message,
        ):
            return await self.run(
                message=message,
                conversation_id=pending_run.conversation_id,
                page_context=pending_run.page_context,
                recent_messages=[],
                recent_artifacts=pending_run.recent_artifacts,
                user=user,
                authorization_header=authorization_header,
            )

        if step.tool_name in LIVE_QUIZ_TOOLS:
            run.plan = self.plan_compiler.normalize_live_quiz_identity(
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
        resumed_preparation = self.step_preparation.prepare(
            tool_name=step.tool_name,
            arguments=step.arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        resolved_arguments = resumed_preparation.arguments
        still_missing = resumed_preparation.missing_fields
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
        return await self.workflow_engine.execute(
            run=run,
            conversation_id=conversation_id,
            user=user,
            authorization_header=authorization_header,
            preflight=self._preflight_step,
            blocked=self._blocked_tool_call_message,
            duration_hook=self._duration_required_response_for_result,
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

        planned_preparation = self.step_preparation.prepare(
            tool_name=confirmed_step.tool_name,
            arguments=confirmed_step.arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        submitted_preparation = self.step_preparation.prepare(
            tool_name=confirmed_step.tool_name,
            arguments=confirmed_arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        confirmed_arguments = self._merge_selectable_arguments(
            tool_name=confirmed_step.tool_name,
            planned_arguments=planned_preparation.arguments,
            submitted_arguments=submitted_preparation.arguments,
        )
        confirmed_preparation = self.step_preparation.prepare(
            tool_name=confirmed_step.tool_name,
            arguments=confirmed_arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        if confirmed_preparation.status is not PreparationStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not resolve arguments for assistant step {confirmed_step.step_id}.",
            )
        confirmed_arguments = confirmed_preparation.arguments

        enforce_tool_policy(confirmed_tool_name, user)
        tool_result = await self.mcp_client.call_tool(
            tool_name=confirmed_tool_name,
            arguments=confirmed_arguments,
            authorization_header=authorization_header,
        )
        normalized_result = normalize_tool_result(confirmed_step.step_id, confirmed_tool_name, tool_result)
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

        run.current_step_index += 1
        return await self._execute_run_from_current_step(
            run=run,
            conversation_id=pending_run.conversation_id,
            user=user,
            authorization_header=authorization_header,
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
        planner = self.plan_compiler.harden(
            planner,
            message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        missing_intents = self.plan_compiler.missing_explicit_workflow_intents(planner.steps, message)
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
        repaired = self.plan_compiler.harden(
            repaired,
            message,
            page_context=page_context,
            recent_artifacts=recent_artifacts,
        )
        repaired_missing = self.plan_compiler.missing_explicit_workflow_intents(repaired.steps, message)
        if len(repaired_missing) < len(missing_intents):
            return repaired
        return planner

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
        tool = get_tool_definition(step.tool_name)
        for argument_name, config in tool.argument_schema.items():
            choices = config.get("choices")
            if not choices:
                continue
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
                for choice in choices
            ]
            step.arguments = arguments
            await self.pending_run_store.save(
                self._pending_run_snapshot(run, conversation_id=conversation_id)
            )
            return AssistantChatResponse(
                message=str(config.get("choice_prompt") or f"Choose a value for {argument_name}."),
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
        if tool_name == "library_save_quiz":
            if self._has_generation_argument(arguments.get("quiz_id")):
                return []
            return [
                argument_name
                for argument_name in ("title", "question_type", "questions")
                if not self._has_generation_argument(arguments.get(argument_name))
            ]
        tool = get_tool_definition(tool_name)
        return [
            argument_name
            for argument_name in tool.required_arguments
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
            duration = self.plan_compiler.parse_live_quiz_duration(message)
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

    def _should_replan_missing_argument_follow_up(
        self,
        *,
        tool_name: str,
        missing_arguments: list[str],
        message: str,
    ) -> bool:
        normalized = message.casefold()
        if any(
            phrase in normalized
            for phrase in (
                "you just",
                "above",
                "from my history",
                "from history",
                "from my saved",
                "from saved",
                "from my folder",
                "pull",
                "pulled",
                "are you saying",
                "i said",
                "not generate",
            )
        ):
            return True
        if tool_name == "library_save_quiz" and "questions" in missing_arguments:
            return True
        if DOWNLOAD_INTENT_PATTERN.search(message) or FOLDER_ADD_INTENT_PATTERN.search(message) or LIVE_QUIZ_LINK_INTENT_PATTERN.search(message):
            return True
        return False

    def _first_unexecuted_step_index(self, run: AssistantRun) -> int:
        completed_step_ids = {result.step_id for result in run.tool_results if result.ok}
        for index, step in enumerate(run.plan):
            if step.step_id not in completed_step_ids:
                return index
        return len(run.plan)

    def _merge_selectable_arguments(
        self,
        *,
        tool_name: str,
        planned_arguments: dict[str, Any],
        submitted_arguments: dict[str, Any],
    ) -> dict[str, Any]:
        merged_arguments = dict(planned_arguments)
        tool = get_tool_definition(tool_name)
        for argument_name, config in tool.argument_schema.items():
            choices = config.get("choices")
            if not choices:
                continue
            submitted_value = submitted_arguments.get(argument_name)
            allowed_values = {choice["value"] for choice in choices}
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
        return tool_error_message(result.tool_name, result.data)

    async def _compose_final_response(self, message: str, run: AssistantRun) -> AssistantFinalResponse:
        return await self.model_router.final_response(
            build_final_response_prompt(
                message=message,
                run_results=self._dump_results(run),
            )
        )

    def _deterministic_final_response(self, run: AssistantRun) -> AssistantFinalResponse | None:
        return self.response_presenter.present(
            run.tool_results,
            page_context=run.page_context,
            recent_artifacts=run.recent_artifacts,
        )

    def _deterministic_final_response_for_results(
        self,
        results: list[ToolResult],
    ) -> AssistantFinalResponse | None:
        return self.response_presenter.present(results)

    def _dump_results(self, run: AssistantRun) -> list[dict[str, Any]]:
        return [result.model_dump(mode="json") for result in run.tool_results]

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
