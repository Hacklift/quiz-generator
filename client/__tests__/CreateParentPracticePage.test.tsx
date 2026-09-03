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

  test("selects 20 minutes by default and hides the custom input", () => {
    render(<CreateParentPracticePage />);
    expect(screen.getByLabelText("Duration")).toHaveValue("20");
    expect(screen.queryByLabelText("Custom duration")).not.toBeInTheDocument();
  });

  test("creates public practice with preset-resolved generation values", async () => {
    mockedCreate.mockResolvedValue({
      quizId: "quiz-1",
      title: "Multiplication tables from 2 to 10 — ages 7 to 9",
      questionCount: 10,
      accessCode: "ABC123",
      durationMinutes: 20,
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
      20,
    );
    expect(screen.getByRole("region", { name: "Practice ready" })).toBeInTheDocument();
    expect(screen.getByText(/Access code ABC123/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Start Practice" }));
    expect(mockPush).toHaveBeenCalledWith("/quiz-access/ABC123");
  });

  test("normalizes a predefined duration to minutes", async () => {
    mockedCreate.mockResolvedValue({
      quizId: "quiz-1",
      title: "Multiplication tables",
      questionCount: 10,
      accessCode: "ABC123",
      durationMinutes: 45,
    });
    render(<CreateParentPracticePage />);
    fireEvent.change(screen.getByLabelText("Duration"), {
      target: { value: "45" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Practice" }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledTimes(1));
    expect(mockedCreate.mock.calls[0][1]).toBe(45);
  });

  test("shows Custom only when selected and accepts a valid custom duration", async () => {
    mockedCreate.mockResolvedValue({
      quizId: "quiz-1",
      title: "Multiplication tables",
      questionCount: 10,
      accessCode: "ABC123",
      durationMinutes: 27,
    });
    render(<CreateParentPracticePage />);
    expect(screen.queryByLabelText("Custom duration")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Duration"), {
      target: { value: "custom" },
    });
    const customInput = screen.getByLabelText("Custom duration");
    fireEvent.change(customInput, { target: { value: "27" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Practice" }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledTimes(1));
    expect(mockedCreate.mock.calls[0][1]).toBe(27);
  });

  test.each(["0", "-1", "181", "2.5", "not-a-number"])(
    "rejects invalid custom duration %s",
    async (value) => {
      render(<CreateParentPracticePage />);
      fireEvent.change(screen.getByLabelText("Duration"), {
        target: { value: "custom" },
      });
      fireEvent.change(screen.getByLabelText("Custom duration"), {
        target: { value },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create Practice" }));

      expect(
        await screen.findByText(/whole number between 1 and 180 minutes/i),
      ).toBeInTheDocument();
      expect(mockedCreate).not.toHaveBeenCalled();
    },
  );
});
