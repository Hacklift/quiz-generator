import axios from "axios";

const API_BASE = `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folders`;

// ✅ Get all folders for a user
export const getUserFolders = async (userId: string) => {
  const res = await axios.get(`${API_BASE}/${userId}`);
  return res.data;
};

// ✅ Create a new folder
export const createFolder = async (userId: string, name: string) => {
  const res = await axios.post(`${API_BASE}/create`, { user_id: userId, name });
  return res.data.folder;
};

// ✅ Rename folder (PUT)
export const renameFolder = async (folderId: string, newName: string) => {
  const res = await axios.put(`${API_BASE}/${folderId}/rename`, null, {
    params: { new_name: newName },
  });
  return res.data;
};

// ✅ Delete a folder (single)
export const deleteFolder = async (folderId: string) => {
  const res = await axios.delete(`${API_BASE}/${folderId}`);
  return res.data;
};

// ✅ Add quiz to folder
export const addQuizToFolder = async (folderId: string, quiz: any) => {
  const quizId = quiz._id || quiz.id || quiz.quiz_id; // ✅ handle all cases
  console.log("Adding quiz to folder:", { quiz_id: quizId });

  const res = await axios.post(`${API_BASE}/${folderId}/add_quiz`, {
    quiz_id: quizId,
  });

  return res.data;
};

// ✅ Remove quiz from folder
export const removeQuizFromFolder = async (
  folderId: string,
  quizId: string,
) => {
  const res = await axios.post(`${API_BASE}/${folderId}/remove/${quizId}`);
  return res.data;
};

// ✅ Get folder by ID
export const getFolderById = async (folderId: string) => {
  const res = await axios.get(`${API_BASE}/view/${folderId}`);
  return res.data;
};

// Move quiz between folders
export const moveQuiz = async (
  quizId: string,
  sourceFolderId: string,
  targetFolderId: string,
) => {
  console.log("➡️ Moving quiz:", { quizId, sourceFolderId, targetFolderId });
  const res = await axios.patch(`${API_BASE}/move_quiz`, {
    quiz_id: quizId,
    from_folder_id: sourceFolderId,
    to_folder_id: targetFolderId,
  });
  return res.data;
};

// ✅ NEW: Bulk delete multiple folders
export const bulkDeleteFolders = async (folderIds: string[]) => {
  const res = await axios.delete(`${API_BASE}/bulk_delete`, {
    data: { folder_ids: folderIds },
  });
  return res.data;
};
