import axios from "axios";
import {
  LoginResponse,
  LoginPayload,
  RefreshTokenResponse,
  UpdateProfilePayload,
  UpdateProfileResponse,
} from "@features/auth/types/User";
import { API_BASE_URL, api } from "@shared/api/http";

export { api };

const getAuthErrorMessage = (error: any, fallback: string): string => {
  const detail = error?.response?.data?.detail;
  const message = error?.response?.data?.message;

  if (Array.isArray(detail)) {
    return detail[0]?.msg || message || fallback;
  }

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (typeof message === "string" && message.trim()) {
    return message;
  }

  if (axios.isAxiosError(error) && !error.response) {
    return "Could not reach the server. Check your connection and try again.";
  }

  if (typeof error?.message === "string" && error.message.trim()) {
    return error.message;
  }

  return fallback;
};

export const registerUser = async (data: {
  username: string;
  email: string;
  full_name: string;
  password: string;
}) => {
  try {
    const response = await api.post("/auth/register/", data);
    return response.data;
  } catch (error: any) {
    throw new Error(getAuthErrorMessage(error, "Registration failed."));
  }
};

export const verifyOtp = async (email: string, otp: string) =>
  api.post("/auth/verify-otp/", { email, otp });

export const verifyLink = async (token: string) =>
  api.post("/auth/verify-link/", { token });

export const resendVerification = async (email: string) =>
  api.post("/auth/resend-verification", { email });

export const login = async (payload: LoginPayload): Promise<LoginResponse> => {
  try {
    const response = await api.post("/auth/login", payload);
    return response.data as LoginResponse;
  } catch (error: any) {
    throw new Error(getAuthErrorMessage(error, "Login failed."));
  }
};

export const refreshAccessToken = async (): Promise<RefreshTokenResponse> => {
  try {
    const response = await axios.post<RefreshTokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      {},
      {
        headers: {
          "Content-Type": "application/json",
        },
        withCredentials: true,
      },
    );
    return response.data;
  } catch (error: any) {
    throw new Error(getAuthErrorMessage(error, "Token refresh failed."));
  }
};

export const getProfile = async () => {
  const response = await api.get("/auth/profile");
  return response.data;
};

export const requestEmailChange = async (newEmail: string) => {
  const response = await api.post("/auth/email-change/request", {
    new_email: newEmail,
  });
  return response.data;
};

export const verifyEmailChange = async (otp: string) => {
  const response = await api.post("/auth/email-change/verify", { otp });
  return response.data;
};

export const deleteAccount = async () => {
  const response = await api.delete("/auth/account");
  return response.data;
};

export const updateProfile = async (
  data: UpdateProfilePayload,
): Promise<UpdateProfileResponse> => {
  try {
    const response = await api.put("/auth/profile", data);
    return response.data as UpdateProfileResponse;
  } catch (error: any) {
    throw new Error(getAuthErrorMessage(error, "Failed to update profile."));
  }
};

export const requestPasswordReset = async (email: string) =>
  api.post("/auth/request-password-reset", { email });

export const resetPassword = async (data: {
  email: string;
  reset_method: "otp" | "token";
  new_password: string;
  otp?: string;
  token?: string;
}) => api.post("/auth/reset-password", data);

export const logoutUser = async () => {
  const response = await api.post("/auth/logout");
  return response.data;
};

export default api;
