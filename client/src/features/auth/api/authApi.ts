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
    const detail = error.response?.data?.detail;
    const message = Array.isArray(detail)
      ? detail[0]?.msg || "Invalid input."
      : typeof detail === "string"
        ? detail
        : error.message || "Registration failed.";
    throw new Error(message);
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
    throw new Error(error.response?.data?.detail || "Login failed");
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
    throw new Error(error.response?.data?.detail || "Token refresh failed");
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
    throw new Error(error.response?.data?.detail || "Failed to update profile");
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
