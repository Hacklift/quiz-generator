jest.mock("axios", () => {
  const api = {
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    post: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };

  const axiosDefault = {
    create: jest.fn(() => api),
    post: jest.fn(),
  };

  return {
    __esModule: true,
    default: axiosDefault,
    AxiosError: class AxiosError extends Error {},
    __mockApi: api,
    __mockAxios: axiosDefault,
  };
});

import {
  registerUser,
  login,
  refreshAccessToken,
  api,
} from "../lib/functions/auth";

const axiosMock = jest.requireMock("axios");
const mockApi = axiosMock.__mockApi as {
  post: jest.Mock;
  get: jest.Mock;
  put: jest.Mock;
  delete: jest.Mock;
};
const mockAxiosPost = axiosMock.__mockAxios.post as jest.Mock;

describe("auth functions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("registerUser maps array detail validation error", async () => {
    mockApi.post.mockRejectedValue({
      response: { data: { detail: [{ msg: "username required" }] } },
    });

    await expect(
      registerUser({
        username: "u",
        email: "e@x.com",
        full_name: "U",
        password: "P@ssw0rd!",
      }),
    ).rejects.toThrow("username required");
  });

  test("login throws backend detail", async () => {
    mockApi.post.mockRejectedValue({
      response: { data: { detail: "Invalid credentials" } },
    });

    await expect(login({ identifier: "u", password: "bad" })).rejects.toThrow(
      "Invalid credentials",
    );
  });

  test("refreshAccessToken returns response data", async () => {
    mockAxiosPost.mockResolvedValue({
      data: { access_token: "a2", token_type: "bearer" },
    });

    const data = await refreshAccessToken();
    expect(data.access_token).toBe("a2");
  });

  test("api export is axios created instance", () => {
    expect(api).toBe(mockApi);
  });
});
