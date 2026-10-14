import { useTranslation } from "react-i18next";
import React, { useState } from "react";
import toast from "react-hot-toast";
import ShareEmailModal from "./ShareEmailModal";
import { ShareModalProps } from "@shared/types/props/share-modal-props";

const ShareModal: React.FC<ShareModalProps> = ({
  quizId,
  shareableLink,
  closeModal,
}) => {
  const { t: uiText } = useTranslation("ui");

  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareableLink);
      toast.success(uiText("m666f3bf526178bae"));
    } catch (error) {
      toast.error(uiText("m51e5255a4c3338f4"));
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
        <h2 className="text-xl font-semibold mb-4">
          {uiText("mb01ddbba0bd98088")}
        </h2>
        <div className="space-y-4">
          <button
            onClick={handleCopyToClipboard}
            className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition duration-200"
          >
            {uiText("mfa8f2b6c07fb514c")}
          </button>
          <button
            onClick={handleShareViaEmail}
            className="w-full bg-gray-500 text-white py-2 rounded hover:bg-gray-600 transition duration-200"
          >
            {uiText("m57bb2923d3ab288c")}
          </button>
          <button
            onClick={handleShareOnFacebook}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition duration-200"
          >
            {uiText("m27065eecbccd4f91")}
          </button>
          <button
            onClick={handleShareOnWhatsApp}
            className="w-full bg-green-500 text-white py-2 rounded hover:bg-green-600 transition duration-200"
          >
            {uiText("ma0d01c1659c92eb1")}
          </button>
          <button
            onClick={handleShareOnTwitter}
            className="w-full bg-blue-400 text-white py-2 rounded hover:bg-blue-500 transition duration-200"
          >
            {uiText("mdb704af914e98c58")}
          </button>
          <button
            onClick={handleShareOnLinkedIn}
            className="w-full bg-blue-700 text-white py-2 rounded hover:bg-blue-800 transition duration-200"
          >
            {uiText("mab87c050148bd1d3")}
          </button>
        </div>
        <button
          onClick={closeModal}
          className="mt-4 w-full bg-red-500 text-white py-2 rounded hover:bg-red-600 transition duration-200"
        >
          {uiText("m7d9eb7acb13e2462")}
        </button>
      </div>
      <ShareEmailModal
        quizId={quizId}
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
      />
    </div>
  );
};

export default ShareModal;
