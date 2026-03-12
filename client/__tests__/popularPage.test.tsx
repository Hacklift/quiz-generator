import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import PopularQuizzesPage from "../pages/popular";

jest.mock("../components/home/NavBar", () => () => (
  <div data-testid="navbar" />
));
jest.mock("../components/home/Footer", () => () => (
  <div data-testid="footer" />
));

describe("PopularQuizzesPage", () => {
  test("renders page title and initial list", () => {
    render(<PopularQuizzesPage />);
    expect(screen.getByText("Popular Quizzes")).toBeInTheDocument();
    expect(screen.getByText("Tech Trends 2025")).toBeInTheDocument();
  });

  test("search filters quizzes by title", () => {
    render(<PopularQuizzesPage />);
    const search = screen.getByPlaceholderText(/Search by quiz title/i);
    fireEvent.change(search, { target: { value: "Ethics" } });

    expect(screen.getByText("AI Safety and Ethics")).toBeInTheDocument();
    expect(screen.queryByText("Tech Trends 2025")).not.toBeInTheDocument();
  });

  test("reset filters button resets search value", () => {
    render(<PopularQuizzesPage />);
    const search = screen.getByPlaceholderText(
      /Search by quiz title/i,
    ) as HTMLInputElement;
    fireEvent.change(search, { target: { value: "Health" } });
    expect(search.value).toBe("Health");

    fireEvent.click(screen.getByRole("button", { name: /Reset Filters/i }));
    expect(search.value).toBe("");
  });
});
