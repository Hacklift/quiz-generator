import React, { useState } from "react";
import axios from "axios";

const ShareEmailModal = ({
  shareableLink,
  quizId,
  isOpen,
  onClose,
}: {
  shareableLink: string;
  quizId: string;
  isOpen: boolean;
  onClose: () => void;
}) => {
  const [recipientEmail, setRecipientEmail] = useState<string>("");
  const [status, setStatus] = useState<{
    message: string;
    success: boolean;
  } | null>(null);
  const [isSending, setIsSending] = useState<boolean>(false);

  const handleSendEmail = async () => {
    setIsSending(true);
    setStatus(null);

    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

    try {
      const response = await axios.post(`${API_BASE_URL}/share/share-email`, {
        quiz_id: quizId,
        recipient_email: recipientEmail,
        shareableLink,
      });
      setStatus({ message: response.data.message, success: true });
      setRecipientEmail("");
    } catch (error: any) {
      setStatus({
        message:
          error.response?.data?.detail ||
          "Failed to send email. Please try again.",
        success: false,
      });
    } finally {
      setIsSending(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-800 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
        <h3 className="text-xl font-semibold mb-4">Share Quiz via Email</h3>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-700"
        >
          Recipient Email Address:
        </label>
        <input
          type="email"
          id="email"
          value={recipientEmail}
          onChange={(e) => setRecipientEmail(e.target.value)}
          placeholder="Enter recipient's email"
          className="mt-1 block w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        />
        {status && (
          <div
            className={`mt-4 p-2 text-sm rounded ${
              status.success
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {typeof status.message === "string"
              ? status.message
              : "An unexpected error occurred. Please try again."}
          </div>
        )}
        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
          >
            Cancel
          </button>
          <button
            onClick={handleSendEmail}
            className={`px-4 py-2 bg-blue-500 text-white rounded ${
              isSending ? "opacity-50 cursor-not-allowed" : "hover:bg-blue-600"
            }`}
            disabled={isSending || !recipientEmail}
          >
            {isSending ? "Sending..." : "Send Email"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareEmailModal;
