import axios from "axios";
import toast from "react-hot-toast";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const publicApi = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

publicApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    if (error?.response?.status === 403 && detail === "Email not verified") {
      if (typeof window !== "undefined") {
        const mark = "__email_not_verified_toast__";
        if (!(window as any)[mark]) {
          (window as any)[mark] = true;
          toast.error("Please verify your email to continue");
          setTimeout(() => {
            (window as any)[mark] = false;
          }, 2000);
        }
        if (!window.location.pathname.startsWith("/auth/verify-email")) {
          window.location.assign("/auth/verify-email-notice");
        }
      }
    }
    return Promise.reject(error);
  },
);

export default publicApi;
