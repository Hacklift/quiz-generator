"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import FolderCard from "@features/folders/components/FolderCard";
import FolderOptionsMenu from "@features/folders/components/FolderOptionsMenu";
import FolderModal from "@features/folders/components/FolderModal";
import OrganizeModal from "@features/folders/components/OrganizeModal";
import ConfirmDeleteModal from "@features/folders/components/ConfirmDeleteModal";
import { useAuth } from "@features/auth/context/authContext";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useTerms } from "@features/persona/hooks/useTerms";
import {
  getUserFolders,
  deleteFolder,
  bulkDeleteFolders,
} from "@features/folders/api/foldersApi";

interface Folder {
  id: string;
  name: string;
  created_at: string;
  quizzes: any[];
  quiz_count?: number;
}

const getFolderId = (folder: Partial<Folder>) => folder.id || "";

const FoldersPage = () => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const t = useTerms();
  const [folders, setFolders] = useState<Folder[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showOrganizeModal, setShowOrganizeModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedFolders, setSelectedFolders] = useState<string[]>([]);

  useEffect(() => {
    if (!isAuthenticated || !user?.id) return;

    const fetchFolders = async () => {
      try {
        const data = await getUserFolders();
        setFolders(data);
      } catch (err) {
        console.error(err);
        toast.error(uiText("mb44e9fbeb8bfb4ed"));
      }
    };

    fetchFolders();
  }, [isAuthenticated, user]);

  const handleDeleteFolder = async (folderId: string) => {
    try {
      await deleteFolder(folderId);
      setFolders((prev) => prev.filter((f) => getFolderId(f) !== folderId));
      toast.success(uiText("m2cccc1e55371326c"));
    } catch (err) {
      console.error(err);
      toast.error(uiText("md4f50856e9920c73"));
    }
  };

  const handleBulkDeleteFolders = async (folderIds: string[]) => {
    if (!folderIds.length) return;
    try {
      await bulkDeleteFolders(folderIds);
      setFolders((prev) =>
        prev.filter((f) => !folderIds.includes(getFolderId(f))),
      );
      toast.success(uiText("m5c32fb01b6f243dc"));
    } catch (err) {
      console.error(err);
      toast.error(uiText("mc7e4c8d9890435cd"));
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-white text-navy-900">
      <NavBar />

      <RequireAuth
        title={uiText("mc4d6bb200f4c058a")}
        description={uiText("mee6e6a6da4f31ffd")}
      >
        <main className="flex-grow px-6 py-10 max-w-6xl mx-auto w-full">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-semibold text-navy-900">
              {uiText("mf9aef2b30eee9ce8")}
            </h1>
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
              <p>{uiText("md890b00a67442bf0")}</p>
              <p className="text-sm">
                {uiText("ma8963583bf4f8d4b")}
                {t("quiz", "plural")}.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {folders.map((folder) => (
                <FolderCard
                  key={getFolderId(folder)}
                  folder={folder}
                  isSelected={selectedFolders.includes(getFolderId(folder))}
                  onOpen={() => router.push(`/folders/${getFolderId(folder)}`)}
                  onToggleSelect={() =>
                    setSelectedFolders((prev) =>
                      prev.includes(getFolderId(folder))
                        ? prev.filter((id) => id !== getFolderId(folder))
                        : [...prev, getFolderId(folder)],
                    )
                  }
                />
              ))}
            </div>
          )}

          {showCreateModal && (
            <FolderModal
              mode="create"
              onClose={() => setShowCreateModal(false)}
              onFolderCreated={(newFolder) =>
                setFolders([...folders, newFolder])
              }
            />
          )}

          {showOrganizeModal && (
            <OrganizeModal
              title={uiText("mf9885788b35df9b1")}
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
      </RequireAuth>

      <Footer />
    </div>
  );
};

export default FoldersPage;
