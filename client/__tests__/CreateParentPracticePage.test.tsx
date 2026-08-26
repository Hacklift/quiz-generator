import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import CreateParentPracticePage from "@features/parent-practice/pages/CreateParentPracticePage";
import { createParentPractice } from "@features/parent-practice/api/parentPracticeApi";

const mockPush = jest.fn();
jest.mock("next/router", () => ({ useRouter: () => ({ push: mockPush }) }));
jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => <nav>Nav</nav>,
}));
jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => <footer>Footer</footer>,
}));
jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({ userType: "parent", isLoading: false }),
}));
jest.mock("@features/parent-practice/api/parentPracticeApi", () => ({
  createParentPractice: jest.fn(),
}));

const mockedCreate = createParentPractice as jest.MockedFunction<
  typeof createParentPractice
>;

describe("CreateParentPracticePage", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockedCreate.mockReset();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: jest.fn().mockResolvedValue(undefined) },
    });
  });

  test("filters presets when the level changes", () => {
    render(<CreateParentPracticePage />);
    fireEvent.change(screen.getByLabelText("Child age/level"), {
      target: { value: "ages-5-7" },
    });
    expect(screen.getByRole("option", { name: "Addition & Subtraction" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Basic Fractions" })).not.toBeInTheDocument();
  });

  test("creates public practice with preset-resolved generation values", async () => {
    mockedCreate.mockResolvedValue({
      quizId: "quiz-1",
      title: "Multiplication tables from 2 to 10 — ages 7 to 9",
      questionCount: 10,
      accessCode: "ABC123",
    });
    render(<CreateParentPracticePage />);
    fireEvent.click(screen.getByRole("button", { name: "Create Practice" }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledTimes(1));
    expect(mockedCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        question_type: "multichoice",
        num_questions: 10,
        audience_type: "children ages 7–9",
      }),
    );
    expect(screen.getByRole("region", { name: "Practice ready" })).toBeInTheDocument();
    expect(screen.getByText(/Access code ABC123/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start Practice" }));
    expect(mockPush).toHaveBeenCalledWith("/quiz-access/ABC123");
  });
});
