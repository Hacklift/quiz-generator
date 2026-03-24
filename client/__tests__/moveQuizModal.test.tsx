import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import MoveQuizModal from "../components/home/folders/MoveQuizModal";

const mockMoveQuiz = jest.fn();
const mockGetUserFolders = jest.fn();
const mockCreateFolder = jest.fn();
const mockUseAuth = jest.fn();

jest.mock("../lib/functions/folders", () => ({
  moveQuiz: (...args: unknown[]) => mockMoveQuiz(...args),
  getUserFolders: (...args: unknown[]) => mockGetUserFolders(...args),
  createFolder: (...args: unknown[]) => mockCreateFolder(...args),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

describe("MoveQuizModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: "user-1" } });
    mockGetUserFolders.mockResolvedValue([
      { _id: "target-folder", name: "Target Folder", quizzes: [] },
    ]);
  });

  test("moves a quiz to another folder and calls refresh callback", async () => {
    const onClose = jest.fn();
    const onQuizMoved = jest.fn();

    render(
      <MoveQuizModal
        isOpen={true}
        onClose={onClose}
        quiz={{ _id: "quiz-1", title: "Quiz" }}
        sourceFolderId="source-folder"
        onQuizMoved={onQuizMoved}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Target Folder")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Target Folder"));
    fireEvent.click(screen.getByRole("button", { name: /^move$/i }));

    await waitFor(() => {
      expect(mockMoveQuiz).toHaveBeenCalledWith(
        "quiz-1",
        "source-folder",
        "target-folder",
      );
    });
    expect(onQuizMoved).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
