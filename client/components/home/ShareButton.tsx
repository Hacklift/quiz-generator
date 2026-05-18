import React, { useState } from "react";
import toast from "react-hot-toast";
import ShareModal from "./ShareModal";
import publicApi from "../../lib/functions/publicApi";

const ShareButton = ({ quizId: activeQuizId }: { quizId?: string }) => {
  const [quizId, setQuizId] = useState<string>("");
  const [shareableLink, setShareableLink] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const generateQuizAndShare = async () => {
    try {
      let id = activeQuizId?.trim() || "";

      if (!id) {
        toast.error(
          "This quiz must exist in the library before it can be shared.",
        );
        return;
      }

      setQuizId(id);
      const linkResponse = await publicApi.get(`/share/share-quiz/${id}`);
      const newShareableLink = linkResponse.data.link;
      setShareableLink(newShareableLink);

      setIsModalOpen(true);
    } catch (error) {
      console.error("Error generating quiz or fetching sharable link:", error);
      toast.error(
        "An error occurred while generating the shareable link. Please try again.",
      );
    }
  };

  return (
    <div>
      <button
        onClick={generateQuizAndShare}
        className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm"
      >
        Share Quiz
      </button>

      {isModalOpen && shareableLink && (
        <ShareModal
          quizId={quizId}
          shareableLink={shareableLink}
          closeModal={() => setIsModalOpen(false)}
        />
      )}
    </div>
  );
};

export default ShareButton;
