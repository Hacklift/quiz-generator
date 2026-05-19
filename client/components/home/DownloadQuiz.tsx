import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../../lib/functions/auth";
import publicApi from "../../lib/functions/publicApi";
import { useAuth } from "../../contexts/authContext";
import { QueryPattern } from "../../constants/patterns";
import { DownloadQuizProps } from "../../interfaces/props";
import SignInModal from "../auth/SignInModal";
import SignUpModal from "../auth/SignUpModal";

type FileFormat = "txt" | "json" | "pdf" | "docx";

export default function DownloadQuiz({
  quizId,
  question_type,
  numQuestion,
}: DownloadQuizProps) {
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
        toast.error("Please sign up or sign in to download this quiz.");
        setShowSignUpModal(true);
        return;
      }

      if (user.is_verified === false) {
        toast.error("Please verify your email to download this quiz.");
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
      toast.success("Quiz download started.");
    } catch (error: any) {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;

      if (status === 401) {
        toast.error("Authentication required. Please sign up or sign in.");
        setShowSignUpModal(true);
      } else if (status === 403 && detail === "Email not verified") {
        toast.error("Please verify your email before downloading quizzes.");
        if (typeof window !== "undefined") {
          window.location.assign("/auth/verify-email-notice");
        }
      } else {
        toast.error("Download failed. Please try again.");
        console.error("Download failed:", error);
      }
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="flex flex-col items-center p-6 bg-gray-100 rounded-lg shadow-md max-w-md mx-auto mt-8">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">
        Download Your Quiz
      </h2>
      <p className="text-gray-600 mb-6 text-center">
        Select a file format to download the quiz.
      </p>
      <div className="mb-4 w-full">
        <label
          htmlFor="format"
          className="block text-gray-700 font-medium mb-2"
        >
          File Format
        </label>
        <select
          id="format"
          value={selectedFormat}
          onChange={handleFormatChange}
          className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="txt">TXT</option>
          <option value="json">JSON</option>
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
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
        {isDownloading ? "Downloading..." : "Download Quiz"}
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
