import { useTranslation } from "react-i18next";
import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { useAuth } from "@features/auth/context/authContext";
import { QueryPattern } from "@shared/config/patterns";
import { DownloadQuizProps } from "@shared/types/props";
import SignInModal from "@features/auth/components/SignInModal";
import SignUpModal from "@features/auth/components/SignUpModal";

type FileFormat = "txt" | "json" | "pdf" | "docx";

export default function DownloadQuiz({
  quizId,
  question_type,
  numQuestion,
}: DownloadQuizProps) {
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();
  const [selectedFormat, setSelectedFormat] = useState<FileFormat>("txt");
  const [isDownloading, setIsDownloading] = useState(false);
  const [showSignUpModal, setShowSignUpModal] = useState(false);
  const [showSignInModal, setShowSignInModal] = useState(false);

  const handleFormatChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedFormat(event.target.value as FileFormat);
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
    const isRealQuiz = !!quizId?.trim();

    if (isRealQuiz) {
      if (!user) {
        toast.error(uiText("md7804c215ad76cd4"));
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
      const params = isRealQuiz
        ? {
            quiz_id: quizId,
            format: selectedFormat,
          }
        : {
            pattern: QueryPattern.DownloadQuiz,
            format: selectedFormat,
            question_type,
            num_question: numQuestion,
          };

      const client = isRealQuiz ? api : publicApi;
      const response = await client.get("/download-quiz", {
        responseType: "blob",
        params,
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${question_type}-quiz.${selectedFormat}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(uiText("m83b8ccb16b4c9996"));
    } catch (error: any) {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;

      if (status === 401) {
        toast.error(uiText("m2d4e86cbe180124b"));
        setShowSignUpModal(true);
      } else if (status === 403 && detail === "Email not verified") {
        toast.error(uiText("m41a10fafb6ebfdba"));
        if (typeof window !== "undefined") {
          window.location.assign("/auth/verify-email-notice");
        }
      } else {
        toast.error(uiText("md2bde7afd7578d68"));
        console.error("Download failed:", error);
      }
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex flex-col items-center p-6 bg-gray-100 rounded-lg shadow-md max-w-md mx-auto mt-8">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">
        {uiText("m7e0b2f1074050b10")}
      </h2>
      <p className="text-gray-600 mb-6 text-center">
        {uiText("m26166ed5d52fd24f")}
      </p>
      <div className="mb-4 w-full">
        <label
          htmlFor="format"
          className="block text-gray-700 font-medium mb-2"
        >
          {uiText("m5ee49824c34ea5ca")}
        </label>
        <select
          id="format"
          value={selectedFormat}
          onChange={handleFormatChange}
          className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="txt">{uiText("md3dc6ac9490999b5")}</option>
          <option value="json">{uiText("mdb1a21a0bc2ef8fb")}</option>
          <option value="pdf">{uiText("m1d393b0081b632c5")}</option>
          <option value="docx">{uiText("mf0abcf998d363c44")}</option>
        </select>
      </div>
      <button
        onClick={handleDownload}
        disabled={isDownloading}
        className={`w-full px-4 py-2 mt-4 text-white font-semibold rounded-md ${
          isDownloading
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-indigo-600 hover:bg-indigo-700"
        }`}
      >
        {isDownloading
          ? uiText("mf976eb284ebb156b")
          : uiText("m4ce34dc2f2013b8c")}
      </button>

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
