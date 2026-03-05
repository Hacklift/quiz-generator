import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { useRouter } from "next/router";
import { ROUTES } from "../constants/patterns/routes";
import { User } from "../interfaces/models/User";
import {
  getProfile,
  logoutUser,
  refreshAccessToken,
  TokenService,
} from "../lib";
interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    accessToken: string,
    refreshToken?: string | null,
    tokenType?: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const isAuthenticated = !!user && !!TokenService.getAccessToken();

  const loadUserProfile = useCallback(async () => {
    try {
      try {
        const refreshed = await refreshAccessToken();
        if (refreshed?.access_token) {
          TokenService.setTokens(
            refreshed.access_token,
            null,
            refreshed.token_type || "bearer",
          );
          const profile = await getProfile();
          setUser(profile);
          return;
        }
      } catch (error) {
        // Ignore refresh failure; treat as unauthenticated.
      }
      if (TokenService.hasTokens()) {
        const profile = await getProfile();
        setUser(profile);
        return;
      }
      setUser(null);
    } catch (error) {
      console.error("Failed to load user profile:", error);
      TokenService.clearTokens();
      setUser(null);
    }
  }, []);

  const login = async (
    accessToken: string,
    refreshToken: string | null = null,
    tokenType: string = "bearer",
  ) => {
    TokenService.setTokens(accessToken, refreshToken, tokenType);
    await loadUserProfile();
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setUser(null);
      TokenService.clearTokens();
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("user_api_token");
      }
      router.push(ROUTES.HOME || "/");
    }
  };

  const refreshUser = async () => {
    await loadUserProfile();
  };

  useEffect(() => {
    const handleTokenExpired = () => {
      setUser(null);
      TokenService.clearTokens();
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("user_api_token");
      }
      router.push(ROUTES.HOME || "/");
    };

    window.addEventListener("token-expired", handleTokenExpired);
    return () => {
      window.removeEventListener("token-expired", handleTokenExpired);
    };
  }, [router]);

  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      try {
        await loadUserProfile();
      } catch (error) {
        console.error("Auth initialization error:", error);
        TokenService.clearTokens();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, [loadUserProfile]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token: TokenService.getAccessToken(),
        isAuthenticated,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
