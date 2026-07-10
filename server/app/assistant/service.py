from uuid import uuid4

from fastapi import HTTPException, status

from server.app.assistant.error_mapper import user_message_for_policy_error
from server.app.assistant.mcp_client import AssistantMcpClient
from server.app.assistant.model_router import AssistantModelRouter
from server.app.assistant.orchestrator import AssistantOrchestrator
from server.app.assistant.pending_runs import AssistantRunStore
from server.app.assistant.providers import AssistantProviderError
from server.app.assistant.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
)
from server.app.assistant.telemetry import AssistantTelemetry
from server.app.core.config import settings
from server.app.users.models import UserOut


class AssistantService:
    def __init__(
        self,
        *,
        model_router: AssistantModelRouter | None = None,
        mcp_client: AssistantMcpClient | None = None,
        pending_run_store: AssistantRunStore | None = None,
    ):
        self._model_router = model_router
        self.mcp_client = mcp_client or AssistantMcpClient()
        self.pending_run_store = pending_run_store

    @property
    def model_router(self) -> AssistantModelRouter:
        if self._model_router is None:
            self._model_router = AssistantModelRouter()
        return self._model_router

    @property
    def orchestrator(self) -> AssistantOrchestrator:
        return AssistantOrchestrator(
            model_router=self.model_router,
            mcp_client=self.mcp_client,
            pending_run_store=self.pending_run_store,
        )

    async def chat(
        self,
        *,
        request: AssistantChatRequest,
        user: UserOut | None,
        authorization_header: str | None,
    ) -> AssistantChatResponse:
        if not settings.ASSISTANT_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assistant is not enabled.",
            )

        conversation_id = request.conversation_id or str(uuid4())
        telemetry = AssistantTelemetry("chat", conversation_id=conversation_id)
        try:
            if request.confirmed_action is not None:
                response = await self.orchestrator.run_confirmed_action(
                    message=request.message,
                    conversation_id=conversation_id,
                    run_id=request.confirmed_action.run_id,
                    step_id=request.confirmed_action.step_id,
                    action_type=request.confirmed_action.type,
                    tool_name=request.confirmed_action.tool_name,
                    arguments=request.confirmed_action.arguments,
                    user=user,
                    authorization_header=authorization_header,
                )
                telemetry.complete(mode="confirmed_action")
                return response

            page_context = request.page_context.model_dump(exclude_none=True) if request.page_context else None
            response = await self.orchestrator.run(
                message=request.message,
                conversation_id=conversation_id,
                page_context=page_context,
                recent_messages=[
                    message.model_dump(mode="json")
                    for message in request.recent_messages
                ],
                recent_artifacts=[
                    artifact.model_dump(mode="json")
                    for artifact in request.recent_artifacts
                ],
                user=user,
                authorization_header=authorization_header,
            )
            telemetry.complete(mode="orchestrated")
            return response
        except AssistantProviderError as exc:
            telemetry.fail(exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The assistant model is temporarily unavailable. Please retry shortly.",
            ) from exc
        except HTTPException as exc:
            if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                telemetry.fail(exc)
                return AssistantChatResponse(
                    message=user_message_for_policy_error(exc.detail)
                    or "Please log in to use this assistant action.",
                    conversation_id=conversation_id,
                    artifacts=[],
                    actions=[],
                )
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                telemetry.fail(exc)
                return AssistantChatResponse(
                    message=user_message_for_policy_error(exc.detail)
                    or "Please verify your email before using this assistant action.",
                    conversation_id=conversation_id,
                    artifacts=[],
                    actions=[],
                )
            raise
        except Exception as exc:
            telemetry.fail(exc)
            raise
