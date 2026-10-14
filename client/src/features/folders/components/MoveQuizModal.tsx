"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  moveQuiz,
  getUserFolders,
  createFolder,
} from "@features/folders/api/foldersApi";
import { useAuth } from "@features/auth/context/authContext";

const getFolderId = (folder: any) => folder?.id || "";
const getFolderItemId = (quiz: any) => quiz?.id || "";

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
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();

  const [folders, setFolders] = useState<any[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState("");
  const [newFolderName, setNewFolderName] = useState("");
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !user?.id) return;

    const loadFolders = async () => {
      try {
        const res = await getUserFolders();
        setFolders(res);
      } catch (err) {
        console.error(err);
        toast.error(uiText("mb44e9fbeb8bfb4ed"));
      }
    };

    loadFolders();
  }, [isOpen, user]);

  if (!isOpen || !quiz) return null;

  const handleMove = async () => {
    if (!user?.id) {
      toast.error(uiText("m351871500bb0403a"));
      return;
    }

    if (!selectedFolderId && !newFolderName.trim()) {
      toast.error(uiText("m43f409d19811f08e"));
      return;
    }

    setLoading(true);

    try {
      let targetFolderId = selectedFolderId;

      if (isCreatingNew && newFolderName.trim()) {
        const newFolder = await createFolder({ name: newFolderName });
        targetFolderId = getFolderId(newFolder);
      }

      await moveQuiz(getFolderItemId(quiz), sourceFolderId, targetFolderId);

      toast.success(uiText("m2632e181b5a4b0ab"));
      onQuizMoved?.();
      onClose();

      setSelectedFolderId("");
      setNewFolderName("");
      setIsCreatingNew(false);
    } catch (err) {
      console.error("Error moving quiz:", err);
      toast.error(uiText("mfbf7738b667f93ef"));
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
        <h2 className="text-xl font-semibold text-navy-800 mb-4">
          {uiText("me8ebb0f7243c60a2")}
        </h2>

        {!isCreatingNew && (
          <div className="space-y-2 mb-4">
            {folders.length === 0 ? (
              <p className="text-gray-500 text-sm mb-3">
                {uiText("m0d21e8017cdf93eb")}
              </p>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-[50vh] pr-1">
                {folders.map((folder) => (
                  <div
                    key={getFolderId(folder)}
                    onClick={() => setSelectedFolderId(getFolderId(folder))}
                    className={`p-3 border rounded-xl cursor-pointer ${
                      selectedFolderId === getFolderId(folder)
                        ? "border-navy-600 bg-blue-50"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <p className="font-medium text-navy-700">{folder.name}</p>
                    <p className="text-xs text-gray-500">
                      {folder.quizzes?.length || 0}{" "}
                      {uiText("m26bf5c6c71e457df")}
                    </p>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => {
                setSelectedFolderId("");
                setIsCreatingNew(true);
              }}
              className="mt-3 text-sm text-navy-600 font-medium hover:underline"
            >
              {uiText("mf42aaa98abd6f502")}
            </button>
          </div>
        )}

        {isCreatingNew && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {uiText("m2b8183033a246513")}
            </label>

            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder={uiText("mb945662a62b0c039")}
              className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-navy-600"
            />

            <button
              onClick={() => {
                setIsCreatingNew(false);
                setNewFolderName("");
              }}
              className="mt-2 text-sm text-navy-600 hover:underline"
            >
              {uiText("m02ef9005d335b502")}
            </button>
          </div>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-gray-200 text-gray-700 hover:bg-gray-300"
          >
            {uiText("m19766ed6ccb2f4a3")}
          </button>

          {(selectedFolderId || (isCreatingNew && newFolderName.trim())) && (
            <button
              onClick={handleMove}
              disabled={loading}
              className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-6 py-2 rounded-xl shadow-md transition text-sm"
            >
              {loading
                ? uiText("mf44f4aefa83526e3")
                : uiText("m6ecc3df6bffdd06c")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MoveQuizModal;
