"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  moveQuiz,
  getUserFolders,
  createFolder,
} from "../../../lib/functions/folders";

interface MoveQuizModalProps {
  isOpen: boolean;
  onClose: () => void;
  quiz: any | null;
  sourceFolderId: string;
  onQuizMoved?: () => void;
}

const MoveQuizModal: React.FC<MoveQuizModalProps> = ({
  isOpen,
  onClose,
  quiz,
  sourceFolderId,
  onQuizMoved,
}) => {
  const [folders, setFolders] = useState<any[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<string>("");
  const [newFolderName, setNewFolderName] = useState("");
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const userId = "dummy_user_123"; // placeholder until auth integration

  useEffect(() => {
    if (isOpen) {
      (async () => {
        try {
          const res = await getUserFolders(userId);
          setFolders(res);
        } catch (err) {
          console.error(err);
          toast.error("Failed to load folders");
        }
      })();
    }
  }, [isOpen]);

  if (!isOpen || !quiz) return null;

  const handleMove = async () => {
    if (!selectedFolderId && !newFolderName.trim()) {
      toast.error("Please select or create a folder");
      return;
    }

    try {
      setLoading(true);
      let targetFolderId = selectedFolderId;

      // ✅ Create new folder if user typed a name
      if (isCreatingNew && newFolderName.trim()) {
        const newFolder = await createFolder(userId, newFolderName);
        targetFolderId = newFolder._id;
      }

      // ✅ Move quiz
      await moveQuiz(quiz._id, sourceFolderId, targetFolderId);

      toast.success("Quiz moved successfully");

      // ✅ Trigger folder refresh after successful move
      if (onQuizMoved) onQuizMoved();

      onClose();
    } catch (err) {
      console.error("Error moving quiz:", err);
      toast.error("Failed to move quiz");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 bg-black/40 z-50 flex justify-center items-center overflow-y-auto transition-opacity duration-300 ${
        isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-md p-6 my-10 relative overflow-y-auto max-h-[90vh] animate-fadeIn">
        <h2 className="text-xl font-semibold text-navy-800 mb-4">Move Quiz</h2>

        {!isCreatingNew && (
          <div className="space-y-2 mb-4">
            {folders.length === 0 ? (
              <p className="text-gray-500 text-sm mb-3">
                No folders available.
              </p>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-[50vh] pr-1">
                {folders.map((folder) => (
                  <div
                    key={folder._id}
                    className={`p-3 border rounded-xl cursor-pointer ${
                      selectedFolderId === folder._id
                        ? "border-navy-600 bg-blue-50"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                    onClick={() => setSelectedFolderId(folder._id)}
                  >
                    <p className="font-medium text-navy-700">{folder.name}</p>
                    <p className="text-xs text-gray-500">
                      {folder.quizzes?.length || 0} quizzes
                    </p>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={() => setIsCreatingNew(true)}
              className="mt-3 text-sm text-navy-600 font-medium hover:underline"
            >
              + Create new folder
            </button>
          </div>
        )}

        {isCreatingNew && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              New Folder Name
            </label>
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="Enter folder name"
              className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-navy-600"
            />
            <button
              onClick={() => setIsCreatingNew(false)}
              className="mt-2 text-sm text-navy-600 hover:underline"
            >
              ← Back to folders
            </button>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300"
            disabled={loading}
          >
            Cancel
          </button>
          {(selectedFolderId || (isCreatingNew && newFolderName.trim())) && (
            <button
              onClick={handleMove}
              className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-6 py-2 rounded-xl shadow-md transition text-sm"
              disabled={loading}
            >
              {loading ? "Moving..." : "Move"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MoveQuizModal;
