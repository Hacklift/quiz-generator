import { useRouter } from "next/router";
import { logoutUser } from "../lib/functions/auth";
import { TokenService } from "../lib/functions/tokenService";

export const useLogout = () => {
  const router = useRouter();

  const logout = async () => {
    const token = TokenService.getAccessToken();
    if (!token) {
      router.push("/auth/login");
      return;
    }

    try {
      await logoutUser();
    } catch (error) {
      console.error("Backend logout failed, clearing token anyway:", error);
    } finally {
      TokenService.clearTokens();
      router.push("/auth/login");
    }
  };

  return { logout };
};
