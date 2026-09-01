import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import CategoriesPage from "@features/categories/pages/CategoriesPage";
import { getCategories } from "@features/categories/api/categoriesApi";

jest.mock("@features/categories/api/categoriesApi", () => ({
  getCategories: jest.fn(),
}));

const mockGetCategories = getCategories as jest.MockedFunction<typeof getCategories>;

let mockPersonaState: { category: string | null; isLoading: boolean } = {
  category: null,
  isLoading: true,
};

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => mockPersonaState,
}));

jest.mock("@features/quiz/components/NavBar", () => () => <nav>NavBar</nav>);
jest.mock("@features/quiz/components/Footer", () => () => <footer>Footer</footer>);

describe("CategoriesPage", () => {
  beforeEach(() => {
    mockGetCategories.mockReset();
    mockPersonaState = { category: null, isLoading: true };
  });

  test("does not fetch until persona finishes loading", async () => {
    mockPersonaState = { category: null, isLoading: true };
    mockGetCategories.mockResolvedValue([]);

    render(<CategoriesPage />);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mockGetCategories).not.toHaveBeenCalled();
  });

  test("requests categories filtered by the user's persona category by default", async () => {
    mockPersonaState = { category: "corporate", isLoading: false };
    mockGetCategories.mockResolvedValue(["Compliance", "Onboarding"]);

    render(<CategoriesPage />);

    await waitFor(() => {
      expect(mockGetCategories).toHaveBeenCalledWith("corporate");
    });

    expect(await screen.findByText("Compliance")).toBeInTheDocument();
    expect(screen.getByText("Onboarding")).toBeInTheDocument();
  });

  test("shows all categories when the toggle is clicked", async () => {
    mockPersonaState = { category: "corporate", isLoading: false };
    mockGetCategories
      .mockResolvedValueOnce(["Compliance", "Onboarding"])
      .mockResolvedValueOnce(["Compliance", "Onboarding", "Mathematics", "Science"]);

    render(<CategoriesPage />);

    await screen.findByText("Compliance");

    const toggleButton = screen.getByRole("button", { name: /show all categories/i });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(mockGetCategories).toHaveBeenLastCalledWith(undefined);
    });

    expect(await screen.findByText("Mathematics")).toBeInTheDocument();
  });
});