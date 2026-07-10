export interface AssistantPageContext {
  route?: string;
  current_quiz_id?: string;
  quiz_summary?: Record<string, unknown>;
}

export interface ConfirmedAssistantAction {
  type?: "confirm" | "choice";
  run_id?: string | null;
  step_id?: string | null;
  tool_name: string;
  arguments: Record<string, unknown>;
}

export interface AssistantConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantArtifact {
  type: string;
  data: Record<string, unknown>;
}

export interface AssistantChatRequest {
  message: string;
  conversation_id?: string | null;
  page_context?: AssistantPageContext;
  recent_messages?: AssistantConversationMessage[];
  recent_artifacts?: AssistantArtifact[];
  confirmed_action?: ConfirmedAssistantAction;
}

export interface AssistantAction {
  type: "confirm" | "choice";
  label: string;
  run_id?: string | null;
  step_id?: string | null;
  tool_name: string;
  arguments: Record<string, unknown>;
}

export interface AssistantChatResponse {
  message: string;
  conversation_id?: string | null;
  artifacts: AssistantArtifact[];
  actions: AssistantAction[];
}

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  artifacts?: AssistantArtifact[];
  actions?: AssistantAction[];
}
