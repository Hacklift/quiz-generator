from typing import Any, Literal

from pydantic import BaseModel, Field


class AssistantPageContext(BaseModel):
    route: str | None = None
    current_quiz_id: str | None = None
    quiz_summary: dict[str, Any] | None = None


class AssistantArtifact(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class AssistantConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ConfirmedAssistantAction(BaseModel):
    type: Literal["confirm", "choice"] | None = None
    run_id: str | None = None
    step_id: str | None = None
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    page_context: AssistantPageContext | None = None
    recent_messages: list[AssistantConversationMessage] = Field(default_factory=list, max_length=12)
    recent_artifacts: list[AssistantArtifact] = Field(default_factory=list, max_length=20)
    confirmed_action: ConfirmedAssistantAction | None = None


class AssistantAction(BaseModel):
    type: Literal["confirm", "choice"]
    label: str
    run_id: str | None = None
    step_id: str | None = None
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AssistantChatResponse(BaseModel):
    message: str
    conversation_id: str | None = None
    artifacts: list[AssistantArtifact] = Field(default_factory=list)
    actions: list[AssistantAction] = Field(default_factory=list)


class PlanStep(BaseModel):
    step_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    depends_on: list[str] = Field(default_factory=list)
    reason: str | None = None


class PlannerDecision(BaseModel):
    intent: str
    needs_tools: bool
    summary: str | None = None
    steps: list[PlanStep] = Field(default_factory=list)
    final_response_style: str = "concise"

    @property
    def tool_name(self) -> str | None:
        return self.steps[0].tool_name if self.steps else None


class ExecutorDecision(BaseModel):
    step_id: str | None = None
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool = True
    step_id: str
    tool_name: str
    data: dict[str, Any] = Field(default_factory=dict)


class AssistantFinalResponse(BaseModel):
    message: str
    artifacts: list[AssistantArtifact] = Field(default_factory=list)
