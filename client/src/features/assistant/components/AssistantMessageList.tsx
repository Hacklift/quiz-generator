import { useEffect, useRef } from "react";
import { AssistantAction, AssistantMessage } from "@features/assistant/types";
import AssistantArtifactList from "@features/assistant/components/AssistantArtifactList";

interface AssistantMessageListProps {
  messages: AssistantMessage[];
  isSending: boolean;
  onConfirmAction: (action: AssistantAction) => void;
}

const AssistantMessageList = ({
  messages,
  isSending,
  onConfirmAction,
}: AssistantMessageListProps) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);

  useEffect(() => {
    if (!shouldAutoScrollRef.current) return;
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isSending]);

  const handleScroll = () => {
    const container = scrollRef.current;
    if (!container) return;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    shouldAutoScrollRef.current = distanceFromBottom < 80;
  };

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 space-y-3 overflow-y-auto px-4 py-4"
    >
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
              message.role === "user"
                ? "bg-blue-600 text-white"
                : "border border-gray-200 bg-white text-gray-800"
            }`}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
            <AssistantArtifactList artifacts={message.artifacts} />
            {message.actions?.length ? (
              <div className="mt-3 space-y-2">
                {message.actions.map((action) => (
                  <button
                    key={`${action.tool_name}-${action.label}`}
                    type="button"
                    onClick={() => onConfirmAction(action)}
                    disabled={isSending}
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${
                      action.type === "choice"
                        ? "bg-blue-600 hover:bg-blue-700"
                        : "bg-emerald-600 hover:bg-emerald-700"
                    }`}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      ))}
      {isSending ? (
        <div className="flex justify-start">
          <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-500 shadow-sm">
            Thinking...
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default AssistantMessageList;
