// context/authContext.tsx
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
import { getProfile, logoutUser, TokenService } from "../lib";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (
    accessToken: string,
    refreshToken: string,
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

  // Check if user is authenticated
  const isAuthenticated = !!user && TokenService.hasTokens();

  // Load user profile
  const loadUserProfile = useCallback(async () => {
    try {
      if (TokenService.hasTokens()) {
        console.log("🔍 Loading user profile...");
        const profile = await getProfile();
        console.log("✅ User profile loaded:", profile);
        setUser(profile);
      } else {
        console.log("⚠️ No tokens found — user not authenticated.");
        setUser(null);
      }
    } catch (error) {
      console.error("Failed to load user profile:", error);
      TokenService.clearTokens();
      setUser(null);
    }
  }, []);

  // Login function - save tokens and load user
  const login = async (
    accessToken: string,
    refreshToken: string,
    tokenType: string = "bearer",
  ) => {
    console.log("🔐 Logging in...");
    TokenService.setTokens(accessToken, refreshToken, tokenType);
    console.log("💾 Tokens saved:", { accessToken, refreshToken, tokenType });
    await loadUserProfile();
  };

  // Logout function
  const logout = async () => {
    try {
      // Call backend logout endpoint to revoke refresh token
      console.log("🚪 Logging out user...");
      await logoutUser();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setUser(null);
      TokenService.clearTokens();
      router.push(ROUTES.LOGIN || "/");
    }
  };

  // Refresh user data
  const refreshUser = async () => {
    await loadUserProfile();
  };

  // Listen for token expiration event (triggered by axios interceptor)
  useEffect(() => {
    const handleTokenExpired = () => {
      setUser(null);
      TokenService.clearTokens();
      router.push(ROUTES.LOGIN || "/");
    };

    window.addEventListener("token-expired", handleTokenExpired);

    return () => {
      window.removeEventListener("token-expired", handleTokenExpired);
    };
  }, [router]);

  // Load user on mount
  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      try {
        if (TokenService.hasTokens()) {
          await loadUserProfile();
        }
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
