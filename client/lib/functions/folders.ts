import axios from "axios";
import { TokenService } from "./tokenService";

const API_BASE = `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folders`;

const authHeaders = () => {
  const token = TokenService.getAccessToken();
  if (!token) {
    throw new Error("Authentication token missing");
  }
  return { Authorization: `Bearer ${token}` };
};

export const getUserFolders = async () => {
  const res = await axios.get(`${API_BASE}/`, {
    headers: authHeaders(),
  });
  return res.data;
};

export const createFolder = async ({ name }: { name: string }) => {
  const res = await axios.post(
    `${API_BASE}/create`,
    { name },
    { headers: authHeaders() },
  );
  return res.data.folder;
};

export const renameFolder = async (folderId: string, newName: string) => {
  const res = await axios.put(
    `${API_BASE}/${folderId}/rename`,
    { new_name: newName },
    { headers: authHeaders() },
  );
  return res.data;
};

export const deleteFolder = async (folderId: string) => {
  const res = await axios.delete(`${API_BASE}/${folderId}`, {
    headers: authHeaders(),
  });
  return res.data;
};

export const addQuizToFolder = async (folderId: string, quiz: any) => {
  const quizId = quiz._id || quiz.id || quiz.quiz_id;
  const res = await axios.post(
    `${API_BASE}/${folderId}/add_quiz`,
    { quiz_id: quizId },
    { headers: authHeaders() },
  );
  return res.data;
};

export const removeQuizFromFolder = async (
  folderId: string,
  quizId: string,
) => {
  const res = await axios.post(
    `${API_BASE}/${folderId}/remove/${quizId}`,
    {},
    { headers: authHeaders() },
  );
  return res.data;
};

export const getFolderById = async (folderId: string) => {
  const res = await axios.get(`${API_BASE}/view/${folderId}`, {
    headers: authHeaders(),
  });
  return res.data;
};

export const moveQuiz = async (
  quizId: string,
  sourceFolderId: string,
  targetFolderId: string,
) => {
  const res = await axios.patch(
    `${API_BASE}/move_quiz`,
    {
      quiz_id: quizId,
      from_folder_id: sourceFolderId,
      to_folder_id: targetFolderId,
    },
    { headers: authHeaders() },
  );
  return res.data;
};

export const bulkDeleteFolders = async (folderIds: string[]) => {
  const res = await axios.delete(`${API_BASE}/bulk_delete`, {
    data: { folder_ids: folderIds },
    headers: authHeaders(),
  });
  return res.data;
};
