export const TokenService = {
  accessTokenMemory: null as string | null,
  tokenTypeMemory: null as string | null,

  getAccessToken(): string | null {
    if (this.accessTokenMemory) return this.accessTokenMemory;
    if (typeof window === "undefined") return null;
    let token = sessionStorage.getItem("access_token");
    if (!token) {
      // One-time migration path for sessions created before sessionStorage switch.
      token = localStorage.getItem("access_token");
      if (token) {
        sessionStorage.setItem("access_token", token);
        localStorage.removeItem("access_token");
      }
    }
    this.accessTokenMemory = token;
    return token;
  },

  getTokenType(): string | null {
    if (this.tokenTypeMemory) return this.tokenTypeMemory;
    if (typeof window === "undefined") return null;
    let tokenType = sessionStorage.getItem("token_type");
    if (!tokenType) {
      tokenType = localStorage.getItem("token_type");
      if (tokenType) {
        sessionStorage.setItem("token_type", tokenType);
        localStorage.removeItem("token_type");
      }
    }
    this.tokenTypeMemory = tokenType;
    return tokenType;
  },

  setTokens(
    accessToken: string,
    refreshToken: string | null = null,
    tokenType: string = "bearer",
  ): void {
    if (typeof window === "undefined") return;
    this.accessTokenMemory = accessToken;
    this.tokenTypeMemory = tokenType;
    sessionStorage.setItem("access_token", accessToken);
    sessionStorage.setItem("token_type", tokenType);
    if (refreshToken) {
      sessionStorage.setItem("refresh_token", refreshToken);
    } else {
      sessionStorage.removeItem("refresh_token");
      localStorage.removeItem("refresh_token");
    }
  },

  updateAccessToken(accessToken: string): void {
    if (typeof window === "undefined") return;
    this.accessTokenMemory = accessToken;
    sessionStorage.setItem("access_token", accessToken);
  },

  clearTokens(): void {
    if (typeof window === "undefined") return;
    this.accessTokenMemory = null;
    this.tokenTypeMemory = null;
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    sessionStorage.removeItem("token_type");
  },

  hasTokens(): boolean {
    return !!this.getAccessToken();
  },
};
