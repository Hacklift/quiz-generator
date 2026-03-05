"use client";

import React, { useState } from "react";
import MoveQuizModal from "./MoveQuizModal";
import OrganizeModal from "./OrganizeModal";

interface FolderViewProps {
  folder: {
    _id: string;
    name: string;
    quizzes: {
      _id: string;
      title: string;
      category: string;
    }[];
  };
}

const FolderView: React.FC<FolderViewProps> = ({ folder }) => {
  const [selectedQuiz, setSelectedQuiz] = useState<any | null>(null);
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [showOrganizeModal, setShowOrganizeModal] = useState(false);
  const [quizzes, setQuizzes] = useState(folder.quizzes || []);

  return (
    <div className="p-6 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-semibold text-navy-800">{folder.name}</h2>
        <button
          onClick={() => setShowOrganizeModal(true)}
          className="text-sm bg-navy-600 text-white px-3 py-2 rounded-lg hover:bg-navy-700"
        >
          Organize
        </button>
      </div>

      {quizzes.length === 0 ? (
        <p className="text-gray-500 text-sm">No quizzes in this folder yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {quizzes.map((quiz) => (
            <div
              key={quiz._id}
              className="p-4 border border-gray-200 rounded-xl hover:shadow-md transition"
            >
              <h3 className="text-lg font-medium text-navy-700 mb-1">
                {quiz.title || "Untitled Quiz"}
              </h3>
              <p className="text-sm text-gray-500 mb-3">
                {quiz.category || "Uncategorized"}
              </p>
              <div className="flex justify-between">
                <button
                  onClick={() => {
                    setSelectedQuiz(quiz);
                    setShowMoveModal(true);
                  }}
                  className="text-sm text-navy-600 hover:underline"
                >
                  Move
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
          sourceFolderId={folder._id}
        />
      )}

      {showOrganizeModal && (
        <OrganizeModal
          title="Organize Quizzes"
          items={quizzes}
          onClose={() => setShowOrganizeModal(false)}
          onOrganized={(sorted) => setQuizzes(sorted)}
          renderItem={(quiz) => <span>{quiz.title || "Untitled Quiz"}</span>}
        />
      )}
    </div>
  );
};

export default FolderView;
