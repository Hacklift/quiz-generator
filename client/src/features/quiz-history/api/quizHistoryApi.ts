import axios from "axios";
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

export const getUserGeneratedQuizHistory = async (): Promise<
  any[] | undefined
> => {
  try {
    const token = TokenService.getAccessToken();
    if (!token) throw new Error("No access token found");

    const response = await api.get("/api/quiz-history");

    return response.data;
  } catch (error) {
    console.error("Failed to fetch generated quiz history:", error);
    return undefined;
  }
};

export const getQuizHistoryItem = async (historyId: string) => {
  const token = TokenService.getAccessToken();
  if (!token) throw new Error("No access token found");

  try {
    const response = await api.get(`/api/quiz-attempts/${historyId}`);
    return response.data;
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 404) {
      throw error;
    }

    const response = await api.get(`/api/quiz-history/${historyId}`);
    return response.data;
  }
};

export const deleteQuizHistoryItem = async (historyId: string) => {
  const token = TokenService.getAccessToken();
  if (!token) throw new Error("No access token found");

  const response = await api.delete(`/api/quiz-attempts/${historyId}`);
  return response.data;
};
