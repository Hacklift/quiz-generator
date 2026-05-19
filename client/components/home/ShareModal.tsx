import React, { useState } from "react";
import toast from "react-hot-toast";
import ShareEmailModal from "./ShareEmailModal";
import { ShareModalProps } from "../../interfaces/props/share-modal-props";

const ShareModal: React.FC<ShareModalProps> = ({
  quizId,
  shareableLink,
  closeModal,
}) => {
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareableLink);
      toast.success("Quiz link copied to clipboard.");
    } catch (error) {
      toast.error("Failed to copy quiz link.");
    }
  };

  const handleShareViaEmail = () => {
    setIsEmailModalOpen(true);
  };

  const handleShareOnFacebook = () => {
    const url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareableLink)}`;
    window.open(url, "_blank");
  };

  const handleShareOnWhatsApp = () => {
    const url = `https://wa.me/?text=${encodeURIComponent(shareableLink)}`;
    window.open(url, "_blank");
  };

  const handleShareOnTwitter = () => {
    const url = `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareableLink)}`;
    window.open(url, "_blank");
  };

  const handleShareOnLinkedIn = () => {
    const url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareableLink)}`;
    window.open(url, "_blank");
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center">
      <div className="bg-white p-6 rounded-lg w-80 text-center">
        <h2 className="text-xl font-semibold mb-4">Share this Quiz</h2>
        <div className="space-y-4">
          <button
            onClick={handleCopyToClipboard}
            className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition duration-200"
          >
            Copy to Clipboard
          </button>
          <button
            onClick={handleShareViaEmail}
            className="w-full bg-gray-500 text-white py-2 rounded hover:bg-gray-600 transition duration-200"
          >
            Share via Email
          </button>
          <button
            onClick={handleShareOnFacebook}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition duration-200"
          >
            Share on Facebook
          </button>
          <button
            onClick={handleShareOnWhatsApp}
            className="w-full bg-green-500 text-white py-2 rounded hover:bg-green-600 transition duration-200"
          >
            Share on WhatsApp
          </button>
          <button
            onClick={handleShareOnTwitter}
            className="w-full bg-blue-400 text-white py-2 rounded hover:bg-blue-500 transition duration-200"
          >
            Share on Twitter
          </button>
          <button
            onClick={handleShareOnLinkedIn}
            className="w-full bg-blue-700 text-white py-2 rounded hover:bg-blue-800 transition duration-200"
          >
            Share on LinkedIn
          </button>
        </div>
        <button
          onClick={closeModal}
          className="mt-4 w-full bg-red-500 text-white py-2 rounded hover:bg-red-600 transition duration-200"
        >
          Close
        </button>
      </div>
      <ShareEmailModal
        shareableLink={shareableLink}
        quizId={quizId}
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
      />
    </div>
  );
};

export default ShareModal;
