"use client";
import { useTranslation } from "react-i18next";

import React, { useState } from "react";
import toast from "react-hot-toast";
import { createFolder, renameFolder } from "@features/folders/api/foldersApi";
import { useAuth } from "@features/auth/context/authContext";

interface FolderModalProps {
  mode: "create" | "rename";
  currentName?: string;
  folderId?: string;
  onClose: () => void;
  onFolderCreated?: (newFolder: any) => void;
  onFolderRenamed?: (updatedFolder: any) => void;
}

const FolderModal: React.FC<FolderModalProps> = ({
  mode,
  currentName = "",
  folderId,
  onClose,
  onFolderCreated,
  onFolderRenamed,
}) => {
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();
  const [folderName, setFolderName] = useState(currentName);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!folderName.trim()) {
      toast.error(uiText("mc85d09e8673eba98"));
      return;
    }

    if (!user?.id) {
      toast.error(uiText("m351871500bb0403a"));
      return;
    }

    setLoading(true);

    try {
      if (mode === "create") {
        const newFolder = await createFolder({ name: folderName });
        toast.success(uiText("m715b5b72c6067074"));
        onFolderCreated?.(newFolder);
      }

      if (mode === "rename" && folderId) {
        const updated = await renameFolder(folderId, folderName);
        toast.success(uiText("m3b1e5afe39167436"));
        onFolderRenamed?.(updated);
      }

      onClose();
    } catch (err) {
      console.error(err);
      toast.error(uiText("mab827e3fe17da220"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-30">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-md p-6 relative">
        <h2 className="text-2xl font-semibold text-navy-900 mb-4">
          {mode === "create"
            ? uiText("mb6b7279516a11532")
            : uiText("m897d4b57e44c4f0d")}
        </h2>

        <input
          type="text"
          value={folderName}
          onChange={(e) => setFolderName(e.target.value)}
          placeholder={uiText("mb945662a62b0c039")}
          className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-navy-600 text-navy-900"
        />

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100"
          >
            {uiText("m19766ed6ccb2f4a3")}
          </button>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-6 py-2 rounded-xl shadow-md transition text-sm"
          >
            {loading
              ? uiText("mdc85af8f2b1d0d67")
              : uiText("m11a6767d5674c7e4")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FolderModal;
