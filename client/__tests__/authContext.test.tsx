import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const push = jest.fn();
const mockGetProfile = jest.fn();
const mockRefreshAccessToken = jest.fn();
const mockLogoutUser = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../lib", () => {
  const actual = jest.requireActual("../lib");
  return {
    ...actual,
    getProfile: (...args: unknown[]) => mockGetProfile(...args),
    refreshAccessToken: (...args: unknown[]) => mockRefreshAccessToken(...args),
    logoutUser: (...args: unknown[]) => mockLogoutUser(...args),
  };
});

import { AuthProvider, useAuth } from "../contexts/authContext";
import { TokenService } from "../lib/functions/tokenService";

function TestConsumer() {
  const { isLoading, isAuthenticated, user, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{String(isLoading)}</div>
      <div data-testid="auth">{String(isAuthenticated)}</div>
      <div data-testid="username">{user?.username || ""}</div>
      <button onClick={() => login("a1", null, "bearer")}>do-login</button>
      <button onClick={() => logout()}>do-logout</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    TokenService.clearTokens();
  });

  test("initializes unauthenticated when refresh fails and no token", async () => {
    mockRefreshAccessToken.mockRejectedValue(new Error("no refresh"));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("auth").textContent).toBe("false");
  });

  test("login sets user state from profile", async () => {
    mockRefreshAccessToken.mockRejectedValue(new Error("no refresh"));
    mockGetProfile.mockResolvedValue({ username: "tester", email: "t@x.com" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText("do-login"));

    await waitFor(() => {
      expect(screen.getByTestId("username").textContent).toBe("tester");
    });
  });

  test("logout clears tokens and routes home", async () => {
    mockRefreshAccessToken.mockRejectedValue(new Error("no refresh"));
    mockLogoutUser.mockResolvedValue({});

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    fireEvent.click(screen.getByText("do-logout"));

    await waitFor(() => {
      expect(push).toHaveBeenCalled();
    });
  });
});
