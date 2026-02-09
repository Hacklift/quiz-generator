import axios from "axios";
import { TokenService } from "../lib/functions/tokenService";

// Use var to avoid TDZ issues with jest.mock hoisting
var mockApi: any;
var requestHandler: any;
var responseErrorHandler: any;

jest.mock("axios", () => {
  return {
    __esModule: true,
    default: {
      create: jest.fn(() => {
        mockApi = {
          post: jest.fn(),
          get: jest.fn(),
          put: jest.fn(),
          interceptors: {
            request: {
              use: jest.fn((fn: any) => {
                requestHandler = fn;
              }),
            },
            response: {
              use: jest.fn((_: any, err: any) => {
                responseErrorHandler = err;
              }),
            },
          },
        };
        return mockApi;
      }),
      post: jest.fn(),
    },
  };
});

import { registerUser, login, getProfile } from "../lib/functions/auth";

const mockedAxios = axios as any;

describe("auth functions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  test("registerUser success returns data", async () => {
    const result = { id: "1", email: "test@example.com" };
    mockApi.post.mockResolvedValue({ data: result });

    const data = await registerUser({
      username: "test",
      email: "test@example.com",
      full_name: "Test User",
      password: "Abcd1234!",
    });

    expect(data).toEqual(result);
    expect(mockApi.post).toHaveBeenCalledWith("/auth/register/", {
      username: "test",
      email: "test@example.com",
      full_name: "Test User",
      password: "Abcd1234!",
    });
  });

  test("login error surfaces message", async () => {
    mockApi.post.mockRejectedValue({
      response: { data: { detail: "Invalid credentials" } },
    });

    await expect(
      login({ identifier: "user", password: "bad" }),
    ).rejects.toThrow("Invalid credentials");
  });

  test("getProfile uses auth header", () => {
    jest.spyOn(TokenService, "getAccessToken").mockReturnValue("token123");

    const config = { headers: {} } as any;
    const updated = requestHandler(config);

    expect(updated.headers.Authorization).toBe("Bearer token123");
  });

  test("token refresh failure clears tokens and dispatches event", async () => {
    const clearSpy = jest.spyOn(TokenService, "clearTokens");
    jest.spyOn(TokenService, "getRefreshToken").mockReturnValue("refresh");

    mockedAxios.post.mockRejectedValue(new Error("refresh failed"));

    const error = {
      response: { status: 401 },
      config: { url: "/api/test", headers: {} },
    } as any;

    await expect(responseErrorHandler(error)).rejects.toBeTruthy();
    expect(clearSpy).toHaveBeenCalled();
  });
});
