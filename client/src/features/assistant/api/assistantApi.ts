import api from "@shared/api/http";
import {
  AssistantChatRequest,
  AssistantChatResponse,
} from "@features/assistant/types";

export const sendAssistantMessage = async (
  payload: AssistantChatRequest,
): Promise<AssistantChatResponse> => {
  const response = await api.post<AssistantChatResponse>(
    "/api/assistant/chat",
    payload,
  );
  return response.data;
};
