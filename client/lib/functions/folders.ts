import { api } from "./auth";

const API_BASE = `/api/folders`;
const getResourceId = (resource: any) => resource?.id || resource?.quiz_id;

export const getUserFolders = async () => {
  const res = await api.get(`${API_BASE}/`);
  return res.data;
};

export const createFolder = async ({ name }: { name: string }) => {
  const res = await api.post(`${API_BASE}/create`, { name });
  return res.data.folder;
};

export const renameFolder = async (folderId: string, newName: string) => {
  const res = await api.put(`${API_BASE}/${folderId}/rename`, {
    new_name: newName,
  });
  return res.data;
};

export const deleteFolder = async (folderId: string) => {
  const res = await api.delete(`${API_BASE}/${folderId}`);
  return res.data;
};

export const addQuizToFolder = async (folderId: string, quiz: any) => {
  const quizId = getResourceId(quiz);
  const res = await api.post(`${API_BASE}/${folderId}/add_quiz`, {
    quiz_id: quizId,
  });
  return res.data;
};

export const removeQuizFromFolder = async (
  folderId: string,
  folderItemId: string,
) => {
  const res = await api.post(
    `${API_BASE}/${folderId}/remove/${folderItemId}`,
    {},
  );
  return res.data;
};

export const getFolderById = async (folderId: string) => {
  const res = await api.get(`${API_BASE}/view/${folderId}`);
  return res.data;
};

export const moveQuiz = async (
  folderItemId: string,
  sourceFolderId: string,
  targetFolderId: string,
) => {
  const res = await api.patch(`${API_BASE}/move_quiz`, {
    quiz_id: folderItemId,
    from_folder_id: sourceFolderId,
    to_folder_id: targetFolderId,
  });
  return res.data;
};

export const bulkDeleteFolders = async (folderIds: string[]) => {
  const res = await api.delete(`${API_BASE}/bulk_delete`, {
    data: { folder_ids: folderIds },
  });
  return res.data;
};
