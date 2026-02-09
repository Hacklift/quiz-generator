import { TokenService } from "../lib/functions/tokenService";

describe("TokenService", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("sets and gets tokens", () => {
    TokenService.setTokens("access", "refresh", "bearer");

    expect(TokenService.getAccessToken()).toBe("access");
    expect(TokenService.getRefreshToken()).toBe("refresh");
    expect(TokenService.getTokenType()).toBe("bearer");
  });

  test("updates access token only", () => {
    TokenService.setTokens("access", "refresh", "bearer");
    TokenService.updateAccessToken("new-access");

    expect(TokenService.getAccessToken()).toBe("new-access");
    expect(TokenService.getRefreshToken()).toBe("refresh");
  });

  test("clears tokens", () => {
    TokenService.setTokens("access", "refresh", "bearer");
    TokenService.clearTokens();

    expect(TokenService.getAccessToken()).toBeNull();
    expect(TokenService.getRefreshToken()).toBeNull();
    expect(TokenService.getTokenType()).toBeNull();
  });

  test("hasTokens returns true only when access and refresh exist", () => {
    expect(TokenService.hasTokens()).toBe(false);
    TokenService.setTokens("access", "refresh", "bearer");
    expect(TokenService.hasTokens()).toBe(true);
  });
});
