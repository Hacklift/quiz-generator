"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import toast from "react-hot-toast";
import { saveQuiz } from "@features/saved-quizzes/api/savedQuizApi";
import { useAuth } from "@features/auth/context/authContext";
import SignInModal from "@features/auth/components/SignInModal";
import SignUpModal from "@features/auth/components/SignUpModal";
import { TokenService } from "@shared/auth/tokenService";

export default function SaveQuizButton({
  quizData,
  quizId,
  contentLocale = "en",
  description,
  isSample = false,
}: {
  quizData: any[];
  quizId?: string;
  contentLocale?: string;
  description?: string;
  isSample?: boolean;
}) {
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();
  const [showInput, setShowInput] = useState(false);
  const [quizTitle, setQuizTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showSignUpModal, setShowSignUpModal] = useState(false);

  const handleSave = async () => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }

    if (!quizData || quizData.length === 0) {
      toast.error(uiText("m573b98650c4821cc"));
      return;
    }

    if (!quizTitle.trim()) {
      toast.error(uiText("m849238dc014418b3"));
      return;
    }

    const questionType =
      quizData[0]?.question_type || quizData[0]?.type || "unknown-type";

    const token = TokenService.getAccessToken();
    if (!token) {
      toast.error(uiText("mf3defa56991cf1ff"));
      return;
    }

    setLoading(true);

    try {
      const formattedQuestions = quizData.map((q) => ({
        ...q,
        question: q.question,
        options: q.options || null,
        question_type: q.question_type || q.type || questionType,
      }));

      await saveQuiz(
        quizTitle.trim(),
        questionType,
        formattedQuestions,
        token,
        quizId,
        contentLocale,
        description,
        isSample,
      );

      toast.success(uiText("mb0a5634981d45ccf"));
      setQuizTitle("");
      setShowInput(false);
    } catch (err) {
      console.error("Failed to save quiz:", err);
      toast.error(uiText("m66694bee1a13d54e"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {!showInput ? (
        <button
          onClick={() => setShowInput(true)}
          className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm"
        >
          {uiText("m91a50b3cecd409a8")}
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder={uiText("m19f940da0f2376fa")}
            value={quizTitle}
            onChange={(e) => setQuizTitle(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm w-36"
          />
          <button
            onClick={handleSave}
            disabled={loading}
            className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-3 py-1.5 rounded-xl shadow-md transition text-sm disabled:bg-gray-400"
          >
            {loading ? uiText("mdc85af8f2b1d0d67") : "✓"}
          </button>
          <button
            onClick={() => {
              setShowInput(false);
              setQuizTitle("");
            }}
            className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-semibold px-3 py-1.5 rounded-xl shadow-md transition text-sm"
          >
            ✕
          </button>
        </div>
      )}

      <SignInModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        switchToSignUp={() => {
          setShowLoginModal(false);
          setShowSignUpModal(true);
        }}
      />
      <SignUpModal
        isOpen={showSignUpModal}
        onClose={() => setShowSignUpModal(false)}
        switchToSignIn={() => {
          setShowSignUpModal(false);
          setShowLoginModal(true);
        }}
      />
    </div>
  );
}
