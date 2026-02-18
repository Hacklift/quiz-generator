import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import {
  LoginResponse,
  LoginPayload,
  RefreshTokenPayload,
  RefreshTokenResponse,
  UpdateProfilePayload,
  UpdateProfileResponse,
} from "../../interfaces/models/User";
import { TokenService } from "./tokenService";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (
  error: AxiosError | null,
  token: string | null = null,
) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = TokenService.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (
        originalRequest.url?.includes("/auth/login") ||
        originalRequest.url?.includes("/auth/register") ||
        originalRequest.url?.includes("/auth/refresh")
      ) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = TokenService.getRefreshToken();

      if (!refreshToken) {
        TokenService.clearTokens();
        processQueue(error, null);
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        const response = await axios.post<RefreshTokenResponse>(
          `${BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken },
          {
            headers: {
              "Content-Type": "application/json",
            },
          },
        );

        const { access_token, token_type } = response.data;

        TokenService.updateAccessToken(access_token);

        if (response.data.refresh_token) {
          TokenService.setTokens(
            access_token,
            response.data.refresh_token,
            token_type,
          );
        }

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        processQueue(null, access_token);
        isRefreshing = false;

        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as AxiosError, null);
        isRefreshing = false;
        TokenService.clearTokens();

        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("token-expired"));
        }

        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

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
  api.post("/auth/verify-otp/", null, { params: { email, otp } });

export const verifyLink = async (token: string) =>
  api.post("/auth/verify-link/", null, { params: { token } });

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

export const refreshAccessToken = async (
  refreshToken: string,
): Promise<RefreshTokenResponse> => {
  try {
    const response = await axios.post<RefreshTokenResponse>(
      `${BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      {
        headers: {
          "Content-Type": "application/json",
        },
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
