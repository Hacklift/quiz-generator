import { MouseEvent, useEffect, useRef, useState } from "react";
import AssistantComposer from "@features/assistant/components/AssistantComposer";
import AssistantMessageList from "@features/assistant/components/AssistantMessageList";
import { AssistantAction, AssistantMessage } from "@features/assistant/types";

interface AssistantPanelProps {
  messages: AssistantMessage[];
  isSending: boolean;
  onSendMessage: (content: string) => Promise<void>;
  onConfirmAction: (action: AssistantAction) => Promise<void>;
  onClose: () => void;
}

const getDefaultPanelPosition = () => {
  if (typeof window === "undefined") return null;
  const width = Math.min(448, window.innerWidth - 32);
  const height = Math.min(560, window.innerHeight - 112);
  return {
    left: Math.max(16, window.innerWidth - width - 24),
    top: Math.max(16, window.innerHeight - height - 96),
  };
};

const AssistantPanel = ({
  messages,
  isSending,
  onSendMessage,
  onConfirmAction,
  onClose,
}: AssistantPanelProps) => {
  const panelRef = useRef<HTMLElement | null>(null);
  const dragStateRef = useRef<{
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const [position, setPosition] = useState<{
    left: number;
    top: number;
  } | null>(() => getDefaultPanelPosition());

  useEffect(() => {
    setPosition(getDefaultPanelPosition());
  }, []);

  useEffect(() => {
    const handleMouseMove = (event: globalThis.MouseEvent) => {
      if (!dragStateRef.current || !panelRef.current) return;
      const rect = panelRef.current.getBoundingClientRect();
      const nextLeft = event.clientX - dragStateRef.current.offsetX;
      const nextTop = event.clientY - dragStateRef.current.offsetY;
      const minVisibleArea = 96;
      const minLeft = Math.min(8, -(rect.width - minVisibleArea));
      const maxLeft = Math.max(8, window.innerWidth - minVisibleArea);
      const maxTop = Math.max(8, window.innerHeight - minVisibleArea);
      setPosition({
        left: Math.min(Math.max(minLeft, nextLeft), maxLeft),
        top: Math.min(Math.max(8, nextTop), maxTop),
      });
    };

    const handleMouseUp = () => {
      dragStateRef.current = null;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const startDrag = (event: MouseEvent<HTMLElement>) => {
    if (!panelRef.current) return;
    const target = event.target as HTMLElement;
    if (target.closest("button")) return;
    const rect = panelRef.current.getBoundingClientRect();
    dragStateRef.current = {
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
  };

  return (
    <section
      ref={panelRef}
      className="fixed z-50 flex min-h-[360px] min-w-[320px] resize overflow-hidden rounded-3xl border border-gray-200 bg-gray-50 shadow-2xl"
      style={{
        left: position?.left ?? 16,
        top: position?.top ?? 16,
        width: "min(448px, calc(100vw - 2rem))",
        height: "min(560px, calc(100vh - 9rem))",
        maxWidth: "calc(100vw - 1rem)",
        maxHeight: "calc(100vh - 1rem)",
      }}
    >
      <div className="flex h-full w-full flex-col overflow-hidden">
        <header
          onMouseDown={startDrag}
          className="flex cursor-move select-none items-center justify-between border-b border-gray-200 bg-white px-4 py-3"
        >
          <div>
            <h2 className="text-sm font-semibold text-gray-900">
              QuizApp Assistant
            </h2>
            <p className="text-xs text-gray-500">
              Powered by internal quiz tools
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-3 py-1 text-sm font-medium text-gray-500 transition hover:bg-gray-100 hover:text-gray-900"
            aria-label="Close assistant"
          >
            Close
          </button>
        </header>
        <AssistantMessageList
          messages={messages}
          isSending={isSending}
          onConfirmAction={onConfirmAction}
        />
        <AssistantComposer
          isSending={isSending}
          onSendMessage={onSendMessage}
        />
      </div>
    </section>
  );
};

export default AssistantPanel;
