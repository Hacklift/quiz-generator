import axios from "axios";
import { GeneratedQuizModel } from "../../interfaces/models";
import { TokenService } from "./tokenService";

export const getUserQuizHistory = async (): Promise<
  GeneratedQuizModel[] | undefined
> => {
  try {
    const token = TokenService.getAccessToken();
    if (!token) throw new Error("No access token found");

    const response = await axios.get(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/quiz-history`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    return response.data;
  } catch (error) {
    console.error("Failed to fetch quiz history:", error);
    return undefined;
  }
};
