import { FormEvent, useState } from "react";

interface AssistantComposerProps {
  isSending: boolean;
  onSendMessage: (message: string) => void;
}

const AssistantComposer = ({
  isSending,
  onSendMessage,
}: AssistantComposerProps) => {
  const [message, setMessage] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setMessage("");
  };

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 p-3">
      <div className="flex items-end gap-2">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          rows={2}
          placeholder="Ask QuizApp..."
          className="min-h-[44px] flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-800 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <button
          type="submit"
          disabled={isSending || !message.trim()}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </form>
  );
};

export default AssistantComposer;
