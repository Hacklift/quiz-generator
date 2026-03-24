import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DownloadQuizButton from "../components/home/DownloadQuizButton";

const mockGet = jest.fn();
const createObjectURL = jest.fn(() => "blob:test");

jest.mock("../lib/functions/publicApi", () => ({
  __esModule: true,
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

describe("DownloadQuizButton", () => {
  const originalCreateElement = document.createElement.bind(document);

  beforeEach(() => {
    jest.clearAllMocks();
    mockGet.mockResolvedValue({ data: new Blob(["test"]) });
    window.URL.createObjectURL = createObjectURL;
    jest
      .spyOn(document, "createElement")
      .mockImplementation((tagName: string) => {
        if (tagName.toLowerCase() === "a") {
          const anchor = originalCreateElement("a");
          anchor.click = jest.fn();
          return anchor;
        }
        return originalCreateElement(tagName);
      });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("toggles format selector and downloads using selected format", async () => {
    render(
      <DownloadQuizButton
        quizId=""
        userId="user-1"
        question_type="multichoice"
        numQuestion={3}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /download quiz/i }));
    expect(screen.getByLabelText(/select format/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/select format/i), {
      target: { value: "pdf" },
    });
    fireEvent.click(screen.getByRole("button", { name: /confirm download/i }));

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        "/download-quiz",
        expect.objectContaining({
          params: expect.objectContaining({
            format: "pdf",
            question_type: "multichoice",
          }),
        }),
      );
    });
  });
});
