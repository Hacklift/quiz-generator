"use client";

import React, { useState } from "react";
import axios from "axios";
import { Observable } from "rxjs";
import { QueryPattern } from "../../constants/patterns";
import { DownloadQuizProps } from "../../interfaces/props";

type FileFormat = "txt" | "csv" | "pdf" | "docx";

export default function DownloadQuizButton({
  question_type,
  numQuestion,
}: DownloadQuizProps) {
  const [selectedFormat, setSelectedFormat] = useState<FileFormat>("txt");
  const [isDownloading, setIsDownloading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  const handleFormatChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedFormat(event.target.value as FileFormat);
  };

  const handleDownload = () => {
    setIsDownloading(true);
    const observable = new Observable<void>((subscriber) => {
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
          setShowOptions(false);
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
    <div className="relative inline-block">
      <button
        onClick={() => setShowOptions((prev) => !prev)}
        className={
          `bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm ` +
          (isDownloading ? "cursor-not-allowed bg-gray-400" : "")
        }
        disabled={isDownloading}
      >
        {isDownloading ? "Downloading..." : "Download Quiz"}
      </button>

      {showOptions && (
        <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-300 rounded-xl shadow-lg p-4 z-10">
          <label
            htmlFor="format"
            className="block text-[#2C3E50] font-medium text-sm mb-2"
          >
            Select format
          </label>
          <select
            id="format"
            value={selectedFormat}
            onChange={handleFormatChange}
            className="w-full border border-gray-300 rounded-md px-3 py-2 mb-4 focus:outline-none focus:ring focus:ring-blue-500 text-sm"
          >
            <option value="txt">TXT</option>
            <option value="csv">CSV</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
          </select>
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold px-3 py-2 rounded-xl shadow-sm text-sm transition disabled:opacity-50"
          >
            Confirm Download
          </button>
        </div>
      )}
    </div>
  );
}
