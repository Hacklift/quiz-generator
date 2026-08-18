import { api } from "@shared/api/http";
import { TokenService } from "@shared/auth/tokenService";

export const getUserQuizHistory = async (): Promise<any[] | undefined> => {
  try {
    const token = TokenService.getAccessToken();
    if (!token) throw new Error("No access token found");

    const response = await api.get("/api/quiz-attempts");

    return response.data;
  } catch (error) {
    console.error("Failed to fetch quiz history:", error);
    return undefined;
  }
};

export const getQuizHistoryItem = async (historyId: string) => {
  const token = TokenService.getAccessToken();
  if (!token) throw new Error("No access token found");

  const response = await api.get(`/api/quiz-attempts/${historyId}`);
  return response.data;
};

export const deleteQuizHistoryItem = async (historyId: string) => {
  const token = TokenService.getAccessToken();
  if (!token) throw new Error("No access token found");

  const response = await api.delete(`/api/quiz-attempts/${historyId}`);
  return response.data;
};
