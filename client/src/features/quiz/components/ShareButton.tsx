import React, { useState } from "react";
import toast from "react-hot-toast";
import ShareModal from "./ShareModal";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { TokenService } from "@shared/auth/tokenService";

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
      // Guests can copy links for already public/unlisted quizzes. Signed-in
      // users send their context so private quizzes receive a useful policy
      // error rather than being indistinguishable from a missing quiz.
      const httpClient = TokenService.hasTokens() ? api : publicApi;
      const linkResponse = await httpClient.get(`/share/share-quiz/${id}`);
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
