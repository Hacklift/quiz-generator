import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from "@testing-library/react";
import SavedQuizzes from "../pages/saved_quiz/index";

const mockGetSavedQuizzes = jest.fn();
const mockDeleteSavedQuiz = jest.fn();
const mockGetUserFolders = jest.fn();
const mockAddQuizToFolder = jest.fn();
const mockCreateFolder = jest.fn();

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => ({
    user: { id: "1" },
    token: "token",
    isAuthenticated: true,
    isLoading: false,
  }),
}));

jest.mock("../lib/functions/savedQuiz", () => ({
  getSavedQuizzes: (...args: any[]) => mockGetSavedQuizzes(...args),
  deleteSavedQuiz: (...args: any[]) => mockDeleteSavedQuiz(...args),
  saveQuiz: jest.fn(),
}));

jest.mock("../lib/functions/folders", () => ({
  getUserFolders: (...args: any[]) => mockGetUserFolders(...args),
  createFolder: (...args: any[]) => mockCreateFolder(...args),
  addQuizToFolder: (...args: any[]) => mockAddQuizToFolder(...args),
}));

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/saved_quiz",
}));

describe("SavedQuizzes page", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("getSavedQuizzes success renders list", async () => {
    mockGetSavedQuizzes.mockResolvedValue([
      { _id: "1", title: "Quiz A", created_at: new Date().toISOString() },
    ]);

    render(<SavedQuizzes />);

    await waitFor(() => {
      expect(screen.getByText("Quiz A")).toBeInTheDocument();
    });
  });

  test("delete quiz triggers API and removes from UI", async () => {
    mockGetSavedQuizzes.mockResolvedValue([
      { _id: "1", title: "Quiz A", created_at: new Date().toISOString() },
    ]);
    mockDeleteSavedQuiz.mockResolvedValue({});

    render(<SavedQuizzes />);

    await waitFor(() => {
      expect(screen.getByText("Quiz A")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByRole("button", { name: "Delete" });
    fireEvent.click(deleteButtons[0]);
    const confirmDelete = screen.getAllByRole("button", { name: "Delete" })[1];
    fireEvent.click(confirmDelete);

    await waitFor(() => {
      expect(mockDeleteSavedQuiz).toHaveBeenCalledWith("1", "token");
      expect(screen.queryByText("Quiz A")).not.toBeInTheDocument();
    });
  });

  test("add-to-folder modal loads folders", async () => {
    mockGetSavedQuizzes.mockResolvedValue([
      { _id: "1", title: "Quiz A", created_at: new Date().toISOString() },
    ]);
    mockGetUserFolders.mockResolvedValue([
      { _id: "f1", name: "Folder 1", created_at: new Date().toISOString() },
    ]);

    render(<SavedQuizzes />);

    await waitFor(() => {
      expect(screen.getByText("Quiz A")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: /Add to Folder/i }));

    const modalTitle = await screen.findByText("Add Quiz to Folder");
    const modal = modalTitle.closest("div") as HTMLElement;

    const selectButton = within(modal).getByRole("button", {
      name: "Select a folder",
    });
    fireEvent.click(selectButton);
    expect(
      within(modal).getByRole("option", { name: "Folder 1" }),
    ).toBeInTheDocument();
  });

  test("add-to-folder submit calls add API for each selected quiz", async () => {
    mockGetSavedQuizzes.mockResolvedValue([
      { _id: "1", title: "Quiz A", created_at: new Date().toISOString() },
      { _id: "2", title: "Quiz B", created_at: new Date().toISOString() },
    ]);
    mockGetUserFolders.mockResolvedValue([
      { _id: "f1", name: "Folder 1", created_at: new Date().toISOString() },
    ]);

    render(<SavedQuizzes />);

    await waitFor(() => {
      expect(screen.getByText("Quiz A")).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole("button", { name: /Add to Folder/i }));

    const modalTitle = await screen.findByText("Add Quiz to Folder");
    const modal = modalTitle.closest("div") as HTMLElement;

    const selectButton = within(modal).getByRole("button", {
      name: "Select a folder",
    });
    fireEvent.click(selectButton);
    fireEvent.click(within(modal).getByRole("option", { name: "Folder 1" }));
    fireEvent.click(within(modal).getByRole("button", { name: /Save/i }));

    await waitFor(() => {
      expect(mockAddQuizToFolder).toHaveBeenCalledWith("f1", { _id: "1" });
      expect(mockAddQuizToFolder).toHaveBeenCalledWith("f1", { _id: "2" });
    });
  });
});
