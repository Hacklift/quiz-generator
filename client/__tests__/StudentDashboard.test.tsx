import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import StudentDashboard from "@features/dashboard/school/views/StudentDashboard";
import type { Persona } from "@shared/config/persona";

const mockPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: mockPush,
    pathname: "/dashboard",
    query: {},
  }),
}));

const mockStudentPersona: Persona = {
  category: "school",
  userType: "student",
};

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({
    persona: mockStudentPersona,
    isLoading: false,
  }),
}));

const mockUser = {
  id: "u789",
  username: "sam_student",
  email: "sam@school.edu",
  is_verified: true,
  full_name: "Sam Rivers",
};

describe("StudentDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders practice, history, presets and live-quiz sections", () => {
    render(<StudentDashboard persona={mockStudentPersona} user={mockUser} />);

    expect(screen.getByText("Practise by subject")).toBeInTheDocument();
    expect(screen.getByText("My gradebook history")).toBeInTheDocument();
    expect(screen.getByText("Retry weak areas")).toBeInTheDocument();
    expect(screen.getByText("Quick-create presets")).toBeInTheDocument();
    expect(screen.getByText("Self-test")).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) => element?.textContent === "Joining a live lesson?",
      ),
    ).toBeInTheDocument();
  });

  test("navigates to the persona-aware generate page when practising a topic", () => {
    render(<StudentDashboard persona={mockStudentPersona} user={mockUser} />);

    fireEvent.click(screen.getByRole("button", { name: /Practise a topic/i }));
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/generate?"),
    );
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("persona=student"),
    );
  });

  test("navigates to quiz history from the history and retry cards", () => {
    render(<StudentDashboard persona={mockStudentPersona} user={mockUser} />);

    fireEvent.click(
      screen.getByRole("button", { name: /My gradebook history/i }),
    );
    expect(mockPush).toHaveBeenCalledWith("/quiz_history");

    fireEvent.click(screen.getByRole("button", { name: /Retry weak areas/i }));
    expect(mockPush).toHaveBeenCalledWith("/quiz_history");
  });

  test("navigates to the self-test preset with the preset query param", () => {
    render(<StudentDashboard persona={mockStudentPersona} user={mockUser} />);

    fireEvent.click(screen.getByRole("button", { name: /Create Self-test/i }));
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("preset=self-test"),
    );
  });

  test("navigates to the live quiz access page", () => {
    render(<StudentDashboard persona={mockStudentPersona} user={mockUser} />);

    fireEvent.click(screen.getByRole("button", { name: /Join a live quiz/i }));
    expect(mockPush).toHaveBeenCalledWith("/quiz-access");
  });
});
