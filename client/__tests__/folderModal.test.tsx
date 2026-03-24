import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import FolderModal from "../components/home/folders/FolderModal";

const mockCreateFolder = jest.fn();
const mockRenameFolder = jest.fn();
const mockUseAuth = jest.fn();

jest.mock("../lib/functions/folders", () => ({
  createFolder: (...args: unknown[]) => mockCreateFolder(...args),
  renameFolder: (...args: unknown[]) => mockRenameFolder(...args),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

describe("FolderModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: "user-1" } });
  });

  test("renders and closes from cancel", () => {
    const onClose = jest.fn();

    render(<FolderModal mode="create" onClose={onClose} />);

    expect(screen.getByText("Create New Folder")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test("creates a folder when valid input is submitted", async () => {
    const onClose = jest.fn();
    const onFolderCreated = jest.fn();
    mockCreateFolder.mockResolvedValue({ _id: "folder-1", name: "Science" });

    render(
      <FolderModal
        mode="create"
        onClose={onClose}
        onFolderCreated={onFolderCreated}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Enter folder name"), {
      target: { value: "Science" },
    });
    fireEvent.click(screen.getByRole("button", { name: /done/i }));

    await waitFor(() => {
      expect(mockCreateFolder).toHaveBeenCalledWith({ name: "Science" });
    });
    expect(onFolderCreated).toHaveBeenCalledWith({
      _id: "folder-1",
      name: "Science",
    });
    expect(onClose).toHaveBeenCalled();
  });
});
