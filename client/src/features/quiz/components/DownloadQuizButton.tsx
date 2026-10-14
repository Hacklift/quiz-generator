"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import toast from "react-hot-toast";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { useAuth } from "@features/auth/context/authContext";
import SignInModal from "@features/auth/components/SignInModal";
import SignUpModal from "@features/auth/components/SignUpModal";
import { DownloadQuizProps } from "@shared/types/props";

type FileFormat = "txt" | "json" | "pdf" | "docx";

const buildDownloadFilename = (
  title: string | undefined,
  questionType: string,
  format: FileFormat,
) => {
  const baseName = (title || `${questionType} quiz` || "Quiz").trim();
  const safeName = baseName
    .replace(/[\\/:*?"<>|\r\n\t]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return `${safeName || "Quiz"}.${format}`;
};

export default function DownloadQuizButton({
  quizId,
  question_type,
  quizData = [],
  title,
  description,
}: DownloadQuizProps) {
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();
  const [selectedFormat, setSelectedFormat] = useState<FileFormat>("txt");
  const [isDownloading, setIsDownloading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [showSignUpModal, setShowSignUpModal] = useState(false);
  const [showSignInModal, setShowSignInModal] = useState(false);

  const handleFormatChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedFormat(event.target.value as FileFormat);
  };

  const downloadBlob = (
    blob: Blob,
    fallbackName: string,
    contentDisposition?: string,
  ) => {
    const matchedFilename = contentDisposition?.match(/filename=([^;]+)/i)?.[1];
    const resolvedName = matchedFilename?.replace(/"/g, "") || fallbackName;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.setAttribute("download", resolvedName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const switchToSignUp = () => {
    setShowSignInModal(false);
    setShowSignUpModal(true);
  };

  const switchToSignIn = () => {
    setShowSignUpModal(false);
    setShowSignInModal(true);
  };

  const handleDownload = async () => {
    const isRealQuiz = quizId && quizId.trim() !== "";

    if (isRealQuiz) {
      if (!user) {
        toast.error(uiText("m450370578d039d81"));
        setShowSignUpModal(true);
        return;
      }

      if (user.is_verified === false) {
        toast.error(uiText("m671210b7bfe8e23d"));
        if (typeof window !== "undefined") {
          window.location.assign("/auth/verify-email-notice");
        }
        return;
      }
    }
    setIsDownloading(true);
    try {
      const isRealQuiz = !!quizId?.trim();
      if (isRealQuiz) {
        const response = await api.get("/download-quiz", {
          responseType: "blob",
          params: {
            quiz_id: quizId,
            format: selectedFormat,
          },
        });

        downloadBlob(
          new Blob([response.data]),
          buildDownloadFilename(title, question_type, selectedFormat),
          response.headers["content-disposition"],
        );
      } else {
        if (!quizData.length) {
          throw new Error("No quiz questions available to download.");
        }

        const response = await publicApi.post(
          "/download-quiz",
          {
            format: selectedFormat,
            title,
            description,
            quiz_type: question_type,
            questions: quizData.map((question) => ({
              question: question.question,
              options: question.options || null,
              answer: String(question.answer ?? question.correct_answer ?? ""),
            })),
          },
          {
            responseType: "blob",
          },
        );

        downloadBlob(
          new Blob([response.data]),
          buildDownloadFilename(title, question_type, selectedFormat),
          response.headers["content-disposition"],
        );
      }

      setShowOptions(false);
      toast.success(uiText("m83b8ccb16b4c9996"));
    } catch (error: any) {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;

      if (status === 401) {
        toast.error(uiText("m9d3a4ed1fbba664c"));
        setShowSignUpModal(true);
      } else if (status === 403 && detail === "Email not verified") {
        toast.error(uiText("m41a10fafb6ebfdba"));
        if (typeof window !== "undefined") {
          window.location.assign("/auth/verify-email-notice");
        }
      } else {
        toast.error(detail || error?.message || "Failed to download quiz.");
        console.error("Download failed:", error);
      }
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setShowOptions((prev) => !prev)}
        className={
          `bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm ` +
          (isDownloading ? "cursor-not-allowed bg-gray-400" : "")
        }
        disabled={isDownloading}
      >
        {isDownloading
          ? uiText("mf976eb284ebb156b")
          : uiText("m4ce34dc2f2013b8c")}
      </button>

      {showOptions && (
        <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-300 rounded-xl shadow-lg p-4 z-10">
          <label
            htmlFor="format"
            className="block text-[#2C3E50] font-medium text-sm mb-2"
          >
            {uiText("mc810c402a124120a")}
          </label>
          <select
            id="format"
            value={selectedFormat}
            onChange={handleFormatChange}
            className="w-full border border-gray-300 rounded-md px-3 py-2 mb-4 focus:outline-none focus:ring focus:ring-blue-500 text-sm"
          >
            <option value="txt">{uiText("md3dc6ac9490999b5")}</option>
            <option value="json">{uiText("mdb1a21a0bc2ef8fb")}</option>
            <option value="pdf">{uiText("m1d393b0081b632c5")}</option>
            <option value="docx">{uiText("mf0abcf998d363c44")}</option>
          </select>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold px-3 py-2 rounded-xl shadow-sm text-sm transition disabled:opacity-50"
          >
            {uiText("md89b4c38861ddf9a")}
          </button>
        </div>
      )}

      <SignUpModal
        isOpen={showSignUpModal}
        onClose={() => setShowSignUpModal(false)}
        switchToSignIn={switchToSignIn}
      />
      <SignInModal
        isOpen={showSignInModal}
        onClose={() => setShowSignInModal(false)}
        switchToSignUp={switchToSignUp}
      />
    </div>
  );
}
