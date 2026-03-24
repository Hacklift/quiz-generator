import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import BrowseModal from "../components/home/modals/BrowseModal";

const mockGet = jest.fn();

jest.mock("@headlessui/react", () => {
  const Dialog = ({
    open,
    children,
  }: React.PropsWithChildren<{ open: boolean }>) =>
    open ? <div>{children}</div> : null;
  Dialog.Panel = ({ children }: React.PropsWithChildren) => (
    <div>{children}</div>
  );
  Dialog.Title = ({ children }: React.PropsWithChildren) => (
    <div>{children}</div>
  );
  return { Dialog };
});

jest.mock("../lib/functions/publicApi", () => ({
  __esModule: true,
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

describe("BrowseModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGet.mockImplementation((url: string) => {
      if (url === "/api/categories") {
        return Promise.resolve({ data: ["Science"] });
      }
      if (url === "/api/category/Science/subcategories") {
        return Promise.resolve({ data: ["Physics"] });
      }
      if (url === "/api/category/Science/subcategory/Physics/types") {
        return Promise.resolve({ data: ["multichoice"] });
      }
      if (
        url ===
        "/api/category/Science/subcategory/Physics/type/multichoice?page=1&page_size=10"
      ) {
        return Promise.resolve({
          data: [
            {
              question: "Question 1",
              answer: "Answer 1",
              options: ["A1", "B1"],
            },
            {
              question: "Question 2",
              answer: "Answer 2",
              options: ["A2", "B2"],
            },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
  });

  test("navigates between browse questions with next and previous", async () => {
    render(<BrowseModal isOpen={true} onClose={jest.fn()} />);

    fireEvent.click(await screen.findByRole("button", { name: "Science" }));
    fireEvent.click(await screen.findByRole("button", { name: "Physics" }));
    fireEvent.click(await screen.findByRole("button", { name: "multichoice" }));

    expect(await screen.findByText("Question 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => {
      expect(screen.getByText("Question 2")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /previous/i }));
    await waitFor(() => {
      expect(screen.getByText("Question 1")).toBeInTheDocument();
    });
  });
});
