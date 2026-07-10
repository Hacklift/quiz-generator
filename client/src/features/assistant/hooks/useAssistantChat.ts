import { useRouter } from "next/router";
import { useState } from "react";
import toast from "react-hot-toast";
import { sendAssistantMessage } from "@features/assistant/api/assistantApi";
import {
  AssistantAction,
  AssistantArtifact,
  AssistantConversationMessage,
  AssistantMessage,
} from "@features/assistant/types";

const createMessageId = () =>
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;

const buildRecentMessages = (
  messages: AssistantMessage[],
): AssistantConversationMessage[] =>
  messages
    .filter((message) => message.content.trim())
    .slice(-10)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));

const buildRecentArtifacts = (
  messages: AssistantMessage[],
): AssistantArtifact[] =>
  messages
    .flatMap((message) => message.artifacts || [])
    .slice(-16);

const normalizeAssistantError = (detail: unknown, fallback: string): string => {
  const message = typeof detail === "string" ? detail : fallback;
  if (
    message.toLowerCase().includes("refresh token missing") ||
    message.toLowerCase().includes("no refresh token")
  ) {
    return "Please log in to access your folders, saved quizzes, history, downloads, sharing, and other personal assistant features.";
  }
  return message;
};

export const useAssistantChat = () => {
  const router = useRouter();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: createMessageId(),
      role: "assistant",
      content: "Ask me to generate quizzes, browse categories, manage saved quizzes, or create live quiz links.",
    },
  ]);
  const [isSending, setIsSending] = useState(false);

  const sendMessage = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || isSending) return;

    const userMessage: AssistantMessage = {
      id: createMessageId(),
      role: "user",
      content: trimmed,
    };
    setMessages((current) => [...current, userMessage]);
    setIsSending(true);

    try {
      const recentMessages = buildRecentMessages(messages);
      const recentArtifacts = buildRecentArtifacts(messages);
      const response = await sendAssistantMessage({
        message: trimmed,
        conversation_id: conversationId,
        page_context: { route: router.asPath },
        recent_messages: recentMessages,
        recent_artifacts: recentArtifacts,
      });
      setConversationId(response.conversation_id || null);
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: response.message,
          artifacts: response.artifacts,
          actions: response.actions,
        },
      ]);
    } catch (error: any) {
      const detail = normalizeAssistantError(
        error?.response?.data?.detail,
        "Assistant request failed.",
      );
      toast.error(detail);
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: detail,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const confirmAction = async (action: AssistantAction) => {
    if (isSending) return;
    setMessages((current) => [
      ...current,
      {
        id: createMessageId(),
        role: "user",
        content: action.label,
      },
    ]);
    setIsSending(true);

    try {
      const recentMessages = buildRecentMessages(messages);
      const recentArtifacts = buildRecentArtifacts(messages);
      const response = await sendAssistantMessage({
        message: action.label,
        conversation_id: conversationId,
        page_context: { route: router.asPath },
        recent_messages: recentMessages,
        recent_artifacts: recentArtifacts,
        confirmed_action: {
          type: action.type,
          run_id: action.run_id,
          step_id: action.step_id,
          tool_name: action.tool_name,
          arguments: action.arguments,
        },
      });
      setConversationId(response.conversation_id || null);
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: response.message,
          artifacts: response.artifacts,
          actions: response.actions,
        },
      ]);
    } catch (error: any) {
      const detail = normalizeAssistantError(
        error?.response?.data?.detail,
        "Assistant action failed.",
      );
      toast.error(detail);
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: detail,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return {
    messages,
    isSending,
    sendMessage,
    confirmAction,
  };
};
