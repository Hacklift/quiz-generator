import { useState } from "react";
import axios from "axios";
import { Observable } from "rxjs";
import { QueryPattern } from "../../constants/patterns";
import { DownloadQuizProps } from "../../interfaces/props";

type FileFormat = "txt" | "csv" | "pdf" | "docx";

export default function DownloadQuiz({
  question_type,
  numQuestion,
}: DownloadQuizProps) {
  const [selectedFormat, setSelectedFormat] = useState<FileFormat>("txt");
  const [isDownloading, setIsDownloading] = useState(false);

  const handleFormatChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedFormat(event.target.value as FileFormat);
  };

  const handleDownload = () => {
    setIsDownloading(true);
    const observable = new Observable((subscriber) => {
      axios
        .get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/download-quiz`, {
          responseType: "blob",
          params: {
            pattern: QueryPattern.DownloadQuiz,
            format: selectedFormat,
            question_type: question_type,
            num_question: numQuestion,
          },
        })
        .then((response) => {
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute(
            "download",
            `${question_type}-quiz.${selectedFormat}`,
          );
          document.body.appendChild(link);
          link.click();
          link.remove();
          subscriber.next();
          subscriber.complete();
        })
        .catch((error) => {
          console.error("Download failed:", error);
          subscriber.error(error);
        })
        .finally(() => {
          setIsDownloading(false);
        });
    });

    observable.subscribe({
      error: (error) => console.error("Observable error:", error),
    });
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
          <option value="csv">CSV</option>
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
    </div>
  );
}
