import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import toast from "react-hot-toast";

import ShareButton from "@features/quiz/components/ShareButton";
import { api } from "@shared/api/http";
import { TokenService } from "@shared/auth/tokenService";

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    error: jest.fn(),
  },
}));

jest.mock("@shared/api/http", () => ({
  api: {
    get: jest.fn(),
  },
}));

jest.mock("@shared/api/publicHttp", () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

jest.mock("@shared/auth/tokenService", () => ({
  TokenService: {
    hasTokens: jest.fn(),
  },
}));

jest.mock("@features/quiz/components/ShareModal", () => () => null);

const mockApiGet = api.get as jest.Mock;
const mockHasTokens = TokenService.hasTokens as jest.Mock;
const mockToastError = toast.error as jest.Mock;

describe("ShareButton", () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    mockApiGet.mockReset();
    mockHasTokens.mockReset();
    mockToastError.mockReset();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test("shows the server shareability guidance for a private quiz", async () => {
    mockHasTokens.mockReturnValue(true);
    mockApiGet.mockRejectedValue({
      response: {
        status: 409,
        data: {
          detail: "Quiz must be public or unlisted before it can be shared by link",
        },
      },
    });

    render(<ShareButton quizId="private-quiz" />);
    fireEvent.click(screen.getByRole("button", { name: "Share Quiz" }));

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/share/share-quiz/private-quiz");
      expect(mockToastError).toHaveBeenCalledWith(
        "Quiz must be public or unlisted before it can be shared by link",
      );
    });
  });
});
