"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import MoveQuizModal from "./MoveQuizModal";
import OrganizeModal from "./OrganizeModal";
import { useTerms } from "@features/persona/hooks/useTerms";

interface FolderViewProps {
  folder: {
    id?: string;
    name: string;
    quizzes: {
      id?: string;
      title: string;
      category: string;
    }[];
  };
}

const getFolderId = (folder: { id?: string }) => folder.id || "";
const getFolderItemId = (quiz: { id?: string }) => quiz.id || "";

const FolderView: React.FC<FolderViewProps> = ({ folder }) => {
  const { t: uiText } = useTranslation("ui");

  const [selectedQuiz, setSelectedQuiz] = useState<any | null>(null);
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [showOrganizeModal, setShowOrganizeModal] = useState(false);
  const [quizzes, setQuizzes] = useState(folder.quizzes || []);
  const t = useTerms();

  return (
    <div className="p-6 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-semibold text-navy-800">{folder.name}</h2>
        <button
          onClick={() => setShowOrganizeModal(true)}
          className="text-sm bg-navy-600 text-white px-3 py-2 rounded-lg hover:bg-navy-700"
        >
          {uiText("m29cc2fca75ebda5f")}
        </button>
      </div>

      {quizzes.length === 0 ? (
        <p className="text-gray-500 text-sm">
          {uiText("m1ea442a134b2a184")}
          {t("quiz", "plural")} {uiText("ma6929558a2437d3d")}
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {quizzes.map((quiz) => (
            <div
              key={getFolderItemId(quiz)}
              className="p-4 border border-gray-200 rounded-xl hover:shadow-md transition"
            >
              <h3 className="text-lg font-medium text-navy-700 mb-1">
                {quiz.title || uiText("m96c2c6ca09471b4d")}
              </h3>
              <p className="text-sm text-gray-500 mb-3">
                {quiz.category || uiText("m8d40d123b2e1e296")}
              </p>
              <div className="flex justify-between">
                <button
                  onClick={() => {
                    setSelectedQuiz(quiz);
                    setShowMoveModal(true);
                  }}
                  className="text-sm text-navy-600 hover:underline"
                >
                  {uiText("m6ecc3df6bffdd06c")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showMoveModal && (
        <MoveQuizModal
          isOpen={showMoveModal}
          onClose={() => setShowMoveModal(false)}
          quiz={selectedQuiz}
          sourceFolderId={getFolderId(folder)}
        />
      )}

      {showOrganizeModal && (
        <OrganizeModal
          title={uiText("md747d230e973dbb1")}
          items={quizzes}
          onClose={() => setShowOrganizeModal(false)}
          onOrganized={(sorted) => setQuizzes(sorted)}
          renderItem={(quiz) => (
            <span>{quiz.title || uiText("m96c2c6ca09471b4d")}</span>
          )}
        />
      )}
    </div>
  );
};

export default FolderView;
