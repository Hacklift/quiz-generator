import { useState } from "react";
import { MessageCircle, Minus } from "lucide-react";
import AssistantPanel from "@features/assistant/components/AssistantPanel";
import { useAssistantChat } from "@features/assistant/hooks/useAssistantChat";

const AssistantLauncher = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { messages, isSending, sendMessage, confirmAction } =
    useAssistantChat();

  return (
    <>
      {isOpen ? (
        <AssistantPanel
          messages={messages}
          isSending={isSending}
          onSendMessage={sendMessage}
          onConfirmAction={confirmAction}
          onClose={() => setIsOpen(false)}
        />
      ) : null}
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="fixed bottom-20 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-xl transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200 sm:right-6"
        aria-label={
          isOpen ? "Close QuizApp assistant" : "Open QuizApp assistant"
        }
      >
        {isOpen ? <Minus size={24} /> : <MessageCircle size={24} />}
      </button>
    </>
  );
};

export default AssistantLauncher;
