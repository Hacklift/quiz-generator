import { GeneratedQuizModel } from "../../interfaces/models";
import { TokenService } from "./tokenService";
import { api } from "./auth";

export const getUserQuizHistory = async (): Promise<
  GeneratedQuizModel[] | undefined
> => {
  try {
    const token = TokenService.getAccessToken();
    if (!token) throw new Error("No access token found");

    const response = await api.get("/api/quiz-history");

    return response.data;
  } catch (error) {
    console.error("Failed to fetch quiz history:", error);
    return undefined;
  }
};
