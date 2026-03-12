import React, { useState } from "react";
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
        const response = await publicApi.get("/share/get-quiz-id");
        id = response.data.id;
      }

      setQuizId(id);

      if (!id) {
        throw new Error(
          "Quiz ID is undefined. Cannot proceed to fetch sharable link.",
        );
      }

      const linkResponse = await publicApi.get(`/share/share-quiz/${id}`);
      const newShareableLink = linkResponse.data.link;
      setShareableLink(newShareableLink);

      setIsModalOpen(true);
    } catch (error) {
      console.error("Error generating quiz or fetching sharable link:", error);
      alert(
        "An error occurred while generating the quiz or sharable link. Please try again.",
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
