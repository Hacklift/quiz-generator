import { renderHook, act } from "@testing-library/react";
import { useLogout } from "../hooks/useLogout";

const push = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../lib/functions/auth", () => ({
  logoutUser: jest.fn().mockResolvedValue({}),
}));

jest.mock("../lib/functions/tokenService", () => ({
  TokenService: {
    getAccessToken: jest.fn(),
    clearTokens: jest.fn(),
  },
}));

import { TokenService } from "../lib/functions/tokenService";

describe("useLogout", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("clears tokens and routes to login", async () => {
    (TokenService.getAccessToken as jest.Mock).mockReturnValue("token");

    const { result } = renderHook(() => useLogout());

    await act(async () => {
      await result.current.logout();
    });

    expect(TokenService.clearTokens).toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith("/auth/login");
  });
});
