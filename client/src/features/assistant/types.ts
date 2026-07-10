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

export interface AssistantArtifactAction {
  type: "copy_to_clipboard";
  label?: string;
  value?: string;
}

export interface AssistantResourceItem {
  id?: string;
  label?: string;
  title?: string;
  name?: string;
  href?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AssistantResourceArtifact {
  type: "resource";
  data: {
    resource?: string;
    label?: string;
    href?: string;
    metadata?: Record<string, unknown>;
    actions?: AssistantArtifactAction[];
    [key: string]: unknown;
  };
}

export interface AssistantResourceListArtifact {
  type: "resource_list";
  data: {
    resource?: string;
    title?: string;
    items?: AssistantResourceItem[];
    pagination?: Record<string, unknown>;
    [key: string]: unknown;
  };
}

export interface AssistantFileActionArtifact {
  type: "file_action";
  data: {
    resource?: string;
    action_id?: string;
    label?: string;
    href?: string;
    method?: "GET" | "POST";
    auto_execute?: boolean;
    max_retries?: number;
    metadata?: {
      quiz_id?: string;
      format?: string;
      filename?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
}

export interface AssistantStatusArtifact {
  type: "status";
  data: {
    resource?: string;
    label?: string;
    message?: string;
    metadata?: Record<string, unknown>;
    [key: string]: unknown;
  };
}

export interface AssistantUnknownArtifact {
  type: string;
  data: Record<string, unknown>;
}

export type AssistantArtifact =
  | AssistantResourceArtifact
  | AssistantResourceListArtifact
  | AssistantFileActionArtifact
  | AssistantStatusArtifact
  | AssistantUnknownArtifact;

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
