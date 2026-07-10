from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fastapi import HTTPException, status

from server.app.assistant.argument_preparation import (
    ArgumentPreparationResult,
    PreparationStatus,
    StepPreparationPipeline,
)
from server.app.assistant.artifacts import infer_artifacts_from_results
from server.app.assistant.confirmation_presenter import ConfirmationPresenter
from server.app.assistant.error_mapper import tool_error_message
from server.app.assistant.mcp_client import AssistantMcpClient
from server.app.assistant.model_router import AssistantModelRouter
from server.app.assistant.pending_runs import AssistantRunStore, PendingAssistantRun
from server.app.assistant.prompts import build_executor_prompt, build_final_response_prompt
from server.app.assistant.response_presenter import AssistantResponsePresenter
from server.app.assistant.schemas import AssistantAction, AssistantChatResponse, PlanStep, ToolResult
from server.app.assistant.tool_policy import enforce_tool_policy, should_request_confirmation
from server.app.users.models import UserOut


class WorkflowRun(Protocol):
    run_id: str
    user_id: str | None
    user_message: str
    status: str
    plan: list[PlanStep]
    current_step_index: int
    tool_results: list[ToolResult]
    pending_confirmation: AssistantAction | None
    page_context: dict[str, Any] | None
    recent_artifacts: list[dict[str, Any]] | None


PreflightHook = Callable[..., Awaitable[AssistantChatResponse | None]]
BlockedHook = Callable[..., str | None]
DurationHook = Callable[..., Awaitable[AssistantChatResponse | None]]


class AssistantWorkflowEngine:
    def __init__(
        self,
        *,
        model_router: AssistantModelRouter,
        mcp_client: AssistantMcpClient,
        pending_run_store: AssistantRunStore,
        preparation: StepPreparationPipeline,
        confirmations: ConfirmationPresenter,
        responses: AssistantResponsePresenter,
    ):
        self.model_router = model_router
        self.mcp_client = mcp_client
        self.pending_run_store = pending_run_store
        self.preparation = preparation
        self.confirmations = confirmations
        self.responses = responses

    async def execute(
        self,
        *,
        run: WorkflowRun,
        conversation_id: str,
        user: UserOut | None,
        authorization_header: str | None,
        preflight: PreflightHook,
        blocked: BlockedHook,
        duration_hook: DurationHook,
    ) -> AssistantChatResponse:
        for index in range(run.current_step_index, len(run.plan)):
            run.current_step_index = index
            step = run.plan[index]
            tool = enforce_tool_policy(step.tool_name, user)
            preparation = await self._prepare(step=step, run=run, user=user)
            arguments = preparation.arguments

            response = await preflight(
                step=step,
                arguments=arguments,
                run=run,
                conversation_id=conversation_id,
                user=user,
            )
            if response is not None:
                return response
            if preparation.status is PreparationStatus.INVALID:
                details = "; ".join(problem.message for problem in preparation.problems)
                return AssistantChatResponse(
                    message=f"I could not use one or more requested values. {details}",
                    conversation_id=conversation_id,
                )

            blocked_message = blocked(
                tool_name=step.tool_name,
                arguments=arguments,
                user_message=run.user_message,
            )
            if blocked_message:
                return AssistantChatResponse(
                    message=blocked_message,
                    conversation_id=conversation_id,
                    artifacts=infer_artifacts_from_results(
                        run.tool_results,
                        suppress_internal_lookup=True,
                        page_context=run.page_context,
                        recent_artifacts=run.recent_artifacts,
                    ),
                )

            if should_request_confirmation(tool, step.requires_confirmation):
                step.arguments = arguments
                action = AssistantAction(
                    type="confirm",
                    label=self.confirmations.label(step.tool_name),
                    run_id=run.run_id,
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    arguments=arguments,
                )
                run.status = "waiting_confirmation"
                run.pending_confirmation = action
                await self.pending_run_store.save(self._snapshot(run, conversation_id))
                return AssistantChatResponse(
                    message=self.confirmations.message(
                        tool_name=step.tool_name,
                        arguments=arguments,
                        results=run.tool_results,
                        page_context=run.page_context,
                        recent_artifacts=run.recent_artifacts,
                    ),
                    conversation_id=conversation_id,
                    actions=[action],
                )

            raw_result = await self.mcp_client.call_tool(
                tool_name=step.tool_name,
                arguments=arguments,
                authorization_header=authorization_header,
            )
            result = normalize_tool_result(step.step_id, step.tool_name, raw_result)
            response = await duration_hook(
                result=result,
                step=step,
                run=run,
                conversation_id=conversation_id,
            )
            if response is not None:
                return response
            run.tool_results.append(result)
            if not result.ok:
                return AssistantChatResponse(
                    message=tool_error_message(result.tool_name, result.data),
                    conversation_id=conversation_id,
                    artifacts=infer_artifacts_from_results(
                        run.tool_results,
                        suppress_internal_lookup=True,
                        page_context=run.page_context,
                        recent_artifacts=run.recent_artifacts,
                    ),
                )

        run.status = "completed"
        final = self.responses.present(
            run.tool_results,
            page_context=run.page_context,
            recent_artifacts=run.recent_artifacts,
        )
        if final is None:
            final = await self.model_router.final_response(
                build_final_response_prompt(
                    message=run.user_message,
                    run_results=[result.model_dump(mode="json") for result in run.tool_results],
                )
            )
        return AssistantChatResponse(
            message=final.message,
            conversation_id=conversation_id,
            artifacts=infer_artifacts_from_results(
                run.tool_results,
                suppress_internal_lookup=True,
                suppress_final_status_tools={"live_quiz_send_invites"},
                page_context=run.page_context,
                recent_artifacts=run.recent_artifacts,
            ),
        )

    async def _prepare(
        self,
        *,
        step: PlanStep,
        run: WorkflowRun,
        user: UserOut | None,
    ) -> ArgumentPreparationResult:
        prepared = self.preparation.prepare(
            tool_name=step.tool_name,
            arguments=step.arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        if prepared.status is not PreparationStatus.AMBIGUOUS:
            return prepared

        executor = await self.model_router.execute(
            build_executor_prompt(
                message=run.user_message,
                planned_tool_name=step.tool_name,
                step_id=step.step_id,
                current_arguments=step.arguments,
                previous_results=[result.model_dump(mode="json") for result in run.tool_results],
                page_context=run.page_context,
            )
        )
        if executor.tool_name != step.tool_name:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Assistant executor selected a different tool than the planner.",
            )
        repaired = self.preparation.prepare(
            tool_name=step.tool_name,
            arguments=executor.arguments,
            previous_results=run.tool_results,
            user_id=str(user.id) if user else None,
        )
        if repaired.status is PreparationStatus.AMBIGUOUS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not resolve arguments for assistant step {step.step_id}.",
            )
        return repaired

    @staticmethod
    def _snapshot(run: WorkflowRun, conversation_id: str) -> PendingAssistantRun:
        return PendingAssistantRun(
            run_id=run.run_id,
            user_id=run.user_id,
            conversation_id=conversation_id,
            message=run.user_message,
            plan=run.plan,
            current_step_index=run.current_step_index,
            tool_results=run.tool_results,
            page_context=run.page_context,
            recent_artifacts=run.recent_artifacts,
        )


def normalize_tool_result(step_id: str, tool_name: str, raw_result: Any) -> ToolResult:
    if isinstance(raw_result, dict):
        normalized = dict(raw_result)
    else:
        normalized = {"result": raw_result}
    is_error = bool(normalized.get("isError") or normalized.get("error"))
    if tool_name == "quiz_generate" and not normalized.get("questions"):
        normalized.setdefault("error", "Quiz generation returned no questions.")
        is_error = True
    return ToolResult(ok=not is_error, step_id=step_id, tool_name=tool_name, data=normalized)
