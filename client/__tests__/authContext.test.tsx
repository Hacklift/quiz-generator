import React from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../contexts/authContext";

const mockGetProfile = jest.fn();
const mockLogoutUser = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("../lib", () => {
  const actual = jest.requireActual("../lib");
  return {
    ...actual,
    getProfile: (...args: any[]) => mockGetProfile(...args),
    logoutUser: (...args: any[]) => mockLogoutUser(...args),
  };
});

jest.mock("../lib/functions/tokenService", () => {
  const actual = jest.requireActual("../lib/functions/tokenService");
  return {
    TokenService: {
      ...actual.TokenService,
      hasTokens: jest.fn(),
      getAccessToken: jest.fn(),
      clearTokens: jest.fn(),
      setTokens: jest.fn(),
    },
  };
});

import { TokenService } from "../lib/functions/tokenService";

const Consumer = () => {
  const { user, isAuthenticated } = useAuth();
  return (
    <div>
      <span data-testid="user">{user?.email || "none"}</span>
      <span data-testid="auth">{isAuthenticated ? "yes" : "no"}</span>
    </div>
  );
};

describe("AuthContext", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("loads profile when tokens exist", async () => {
    (TokenService.hasTokens as jest.Mock).mockReturnValue(true);
    (TokenService.getAccessToken as jest.Mock).mockReturnValue("token");
    mockGetProfile.mockResolvedValue({ email: "user@example.com" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("user@example.com");
    });
  });

  test("clears user on token-expired event", async () => {
    (TokenService.hasTokens as jest.Mock).mockReturnValue(true);
    (TokenService.getAccessToken as jest.Mock).mockReturnValue("token");
    mockGetProfile.mockResolvedValue({ email: "user@example.com" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("user@example.com");
    });

    act(() => {
      window.dispatchEvent(new Event("token-expired"));
    });

    await waitFor(() => {
      expect(TokenService.clearTokens).toHaveBeenCalled();
      expect(screen.getByTestId("user").textContent).toBe("none");
    });
  });
});
