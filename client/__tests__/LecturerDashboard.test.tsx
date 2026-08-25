import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import LecturerDashboard from "@features/dashboard/school/views/LecturerDashboard";
import type { Persona } from "@shared/config/persona";

const mockPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: mockPush,
    pathname: "/dashboard",
    query: {},
  }),
}));

const mockLecturerPersona: Persona = {
  category: "school",
  userType: "lecturer",
};

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({
    persona: mockLecturerPersona,
    isLoading: false,
  }),
}));

const mockUser = {
  id: "u456",
  username: "dr_ada",
  email: "ada@university.edu",
  is_verified: true,
  full_name: "Ada Lovelace",
};

describe("LecturerDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders live session emphasis and presets", () => {
    render(
      <LecturerDashboard persona={mockLecturerPersona} user={mockUser} />,
    );

    expect(screen.getByText("Live session")).toBeInTheDocument();
    expect(screen.getByText("Quick-create presets")).toBeInTheDocument();
    expect(screen.getByText("Lecture recap")).toBeInTheDocument();
    expect(screen.getByText("Seminar prep")).toBeInTheDocument();
  });

  test("navigates to the persona-aware generate page with lecturer presets", () => {
    render(
      <LecturerDashboard persona={mockLecturerPersona} user={mockUser} />,
    );

    const recapBtn = screen.getByRole("button", {
      name: /Create Lecture recap/i,
    });
    fireEvent.click(recapBtn);
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("preset=lecture-recap"),
    );
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("/generate?"));
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("persona=lecturer"));
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("category=school"));

    const seminarBtn = screen.getByRole("button", {
      name: /Create Seminar prep/i,
    });
    fireEvent.click(seminarBtn);
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("preset=seminar-prep"),
    );
  });

  test("surfaces live session controls with 1-click navigation", () => {
    render(
      <LecturerDashboard persona={mockLecturerPersona} user={mockUser} />,
    );

    const startBtn = screen.getByRole("button", {
      name: /Start a live lecture/i,
    });
    fireEvent.click(startBtn);
    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes");

    const liveResultsBtn = screen.getByRole("button", {
      name: /View live session results/i,
    });
    fireEvent.click(liveResultsBtn);
    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes");

    const historyBtn = screen.getByRole("button", {
      name: /View homework history/i,
    });
    fireEvent.click(historyBtn);
    expect(mockPush).toHaveBeenCalledWith("/quiz_history");
  });

  test("uses dynamic school terminology (cohort/lecture) in descriptions", () => {
    render(
      <LecturerDashboard persona={mockLecturerPersona} user={mockUser} />,
    );

    expect(
      screen.getByText((content, element) => {
        return (
          element?.tagName.toLowerCase() === "p" &&
          content.includes("pre-configured for") &&
          content.includes("cohorts")
        );
      }),
    ).toBeInTheDocument();
  });
});