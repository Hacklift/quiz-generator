export const TokenService = {
  accessTokenMemory: null as string | null,
  refreshTokenMemory: null as string | null,
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

  getRefreshToken(): string | null {
    if (this.refreshTokenMemory) return this.refreshTokenMemory;
    if (typeof window === "undefined") return null;
    let token = sessionStorage.getItem("refresh_token");
    if (!token) {
      token = localStorage.getItem("refresh_token");
      if (token) {
        sessionStorage.setItem("refresh_token", token);
        localStorage.removeItem("refresh_token");
      }
    }
    this.refreshTokenMemory = token;
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
    refreshToken: string,
    tokenType: string = "bearer",
  ): void {
    if (typeof window === "undefined") return;
    this.accessTokenMemory = accessToken;
    this.refreshTokenMemory = refreshToken;
    this.tokenTypeMemory = tokenType;
    sessionStorage.setItem("access_token", accessToken);
    sessionStorage.setItem("refresh_token", refreshToken);
    sessionStorage.setItem("token_type", tokenType);
  },

  updateAccessToken(accessToken: string): void {
    if (typeof window === "undefined") return;
    this.accessTokenMemory = accessToken;
    sessionStorage.setItem("access_token", accessToken);
  },

  clearTokens(): void {
    if (typeof window === "undefined") return;
    this.accessTokenMemory = null;
    this.refreshTokenMemory = null;
    this.tokenTypeMemory = null;
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    sessionStorage.removeItem("token_type");
  },

  hasTokens(): boolean {
    return !!(this.getAccessToken() && this.getRefreshToken());
  },
};
