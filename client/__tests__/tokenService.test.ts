import { TokenService } from "../lib/functions/tokenService";

describe("TokenService", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    TokenService.accessTokenMemory = null;
    TokenService.tokenTypeMemory = null;
  });

  test("setTokens stores access token and token type", () => {
    TokenService.setTokens("a1", null, "Bearer");
    expect(sessionStorage.getItem("access_token")).toBe("a1");
    expect(sessionStorage.getItem("token_type")).toBe("Bearer");
  });

  test("migrates access token from localStorage to sessionStorage", () => {
    localStorage.setItem("access_token", "legacy");
    const token = TokenService.getAccessToken();
    expect(token).toBe("legacy");
    expect(sessionStorage.getItem("access_token")).toBe("legacy");
    expect(localStorage.getItem("access_token")).toBeNull();
  });

  test("clearTokens removes all token keys", () => {
    TokenService.setTokens("a1", "r1", "bearer");
    TokenService.clearTokens();
    expect(sessionStorage.getItem("access_token")).toBeNull();
    expect(sessionStorage.getItem("refresh_token")).toBeNull();
    expect(sessionStorage.getItem("token_type")).toBeNull();
    expect(TokenService.hasTokens()).toBe(false);
  });
});
