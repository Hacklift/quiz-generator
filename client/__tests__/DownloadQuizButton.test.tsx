import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DownloadQuizButton from "../components/home/DownloadQuizButton";

const mockGet = jest.fn();

jest.mock("axios", () => ({
  get: (...args: any[]) => mockGet(...args),
}));

describe("DownloadQuizButton", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.URL as any).createObjectURL = jest.fn(() => "blob:url");
    document.body.innerHTML = "";
  });

  test("chooses format and triggers download", async () => {
    mockGet.mockResolvedValue({ data: new Blob(["data"]) });

    render(<DownloadQuizButton question_type="multichoice" numQuestion={3} />);

    fireEvent.click(screen.getByRole("button", { name: /Download Quiz/i }));
    fireEvent.change(screen.getByLabelText(/Select format/i), {
      target: { value: "pdf" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Confirm Download/i }));

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining("/download-quiz"),
        expect.objectContaining({
          params: expect.objectContaining({
            format: "pdf",
            question_type: "multichoice",
            num_question: 3,
          }),
        }),
      );
    });
  });
});
