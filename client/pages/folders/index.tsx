"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";
import FolderCard from "../../components/home/folders/FolderCard";
import FolderOptionsMenu from "../../components/home/folders/FolderOptionsMenu";
import FolderModal from "../../components/home/folders/FolderModal";
import OrganizeModal from "../../components/home/folders/OrganizeModal";
import ConfirmDeleteModal from "../../components/home/folders/ConfirmDeleteModal";
import { useAuth } from "../../contexts/authContext";
import {
  getUserFolders,
  deleteFolder,
  bulkDeleteFolders,
} from "../../lib/functions/folders";

interface Folder {
  _id: string;
  name: string;
  created_at: string;
  quizzes: any[];
}

const FoldersPage = () => {
  const { user } = useAuth();
  const [folders, setFolders] = useState<Folder[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showOrganizeModal, setShowOrganizeModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedFolders, setSelectedFolders] = useState<string[]>([]);

  // Fetch user folders
  useEffect(() => {
    if (!user?.id) return;

    const fetchFolders = async () => {
      try {
        const data = await getUserFolders();
        setFolders(data);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load folders");
      }
    };

    fetchFolders();
  }, [user]);

  // Single folder delete
  const handleDeleteFolder = async (folderId: string) => {
    try {
      await deleteFolder(folderId);
      setFolders((prev) => prev.filter((f) => f._id !== folderId));
      toast.success("Folder deleted successfully");
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete folder");
    }
  };

  // Bulk folder delete
  const handleBulkDeleteFolders = async (folderIds: string[]) => {
    if (!folderIds.length) return;
    try {
      await bulkDeleteFolders(folderIds);
      setFolders((prev) => prev.filter((f) => !folderIds.includes(f._id)));
      toast.success("Selected folders deleted successfully");
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete folders");
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-white text-navy-900">
      <NavBar />

      <main className="flex-grow px-6 py-10 max-w-6xl mx-auto w-full">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-semibold text-navy-900">My Folders</h1>
          <FolderOptionsMenu
            onCreate={() => setShowCreateModal(true)}
            onOrganize={() => setShowOrganizeModal(true)}
            onDelete={() =>
              selectedFolders.length > 0 && setShowDeleteModal(true)
            }
          />
        </div>

        {folders.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            <p>No folders yet.</p>
            <p className="text-sm">
              Create a folder to organize your saved quizzes.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {folders.map((folder) => (
              <FolderCard
                key={folder._id}
                folder={folder}
                isSelected={selectedFolders.includes(folder._id)}
                onSelect={() =>
                  setSelectedFolders((prev) =>
                    prev.includes(folder._id)
                      ? prev.filter((id) => id !== folder._id)
                      : [...prev, folder._id],
                  )
                }
              />
            ))}
          </div>
        )}

        {/* ===== Modals ===== */}
        {showCreateModal && (
          <FolderModal
            mode="create"
            onClose={() => setShowCreateModal(false)}
            onFolderCreated={(newFolder) => setFolders([...folders, newFolder])}
          />
        )}

        {showOrganizeModal && (
          <OrganizeModal
            title="Organize Folders"
            items={folders}
            onClose={() => setShowOrganizeModal(false)}
            onOrganized={(sorted) => setFolders(sorted)}
            renderItem={(folder) => <span>{folder.name}</span>}
          />
        )}

        {showDeleteModal && (
          <ConfirmDeleteModal
            selectedItems={selectedFolders}
            type="folder"
            onClose={() => setShowDeleteModal(false)}
            onDeleted={(deletedIds) => {
              if (deletedIds.length === 1) {
                handleDeleteFolder(deletedIds[0]);
              } else {
                handleBulkDeleteFolders(deletedIds);
              }
              setShowDeleteModal(false);
              setSelectedFolders([]);
            }}
          />
        )}
      </main>

      <Footer />
    </div>
  );
};

export default FoldersPage;
