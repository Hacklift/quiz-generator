"use client";

import React, { useState } from "react";
import toast from "react-hot-toast";
import { createFolder, renameFolder } from "../../../lib/functions/folders";

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
  const [folderName, setFolderName] = useState(currentName);
  const [loading, setLoading] = useState(false);

  const dummyUserId = "12345";
  const handleSubmit = async () => {
    if (!folderName.trim()) {
      toast.error("Please enter a folder name");
      return;
    }

    setLoading(true);
    try {
      if (mode === "create") {
        const newFolder = await createFolder(dummyUserId, folderName);
        toast.success("Folder created successfully");
        onFolderCreated?.(newFolder);
      } else if (mode === "rename" && folderId) {
        const updated = await renameFolder(folderId, folderName);
        toast.success("Folder renamed successfully");
        onFolderRenamed?.(updated);
      }
      onClose();
    } catch (err) {
      console.error(err);
      toast.error("Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-30">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-md p-6 relative">
        <h2 className="text-2xl font-semibold text-navy-900 mb-4">
          {mode === "create" ? "Create New Folder" : "Rename Folder"}
        </h2>

        <input
          type="text"
          value={folderName}
          onChange={(e) => setFolderName(e.target.value)}
          placeholder="Enter folder name"
          className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-navy-600 text-navy-900"
        />

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-6 py-2 rounded-xl shadow-md transition text-sm"
            disabled={loading}
          >
            {loading ? "Saving..." : "Done"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FolderModal;
