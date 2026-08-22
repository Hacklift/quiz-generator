import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import TeacherDashboard from "@features/dashboard/school/views/TeacherDashboard";
import type { Persona } from "@shared/config/persona";

const mockPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: mockPush,
    pathname: "/dashboard",
    query: {},
  }),
}));

const mockTeacherPersona: Persona = {
  category: "school",
  userType: "teacher",
};

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({
    persona: mockTeacherPersona,
    isLoading: false,
  }),
}));

const mockUser = {
  id: "u123",
  username: "mr_smith",
  email: "smith@school.edu",
  is_verified: true,
  full_name: "John Smith",
};

describe("TeacherDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders teacher dashboard kicker, headings, and presets", () => {
    render(
      <TeacherDashboard persona={mockTeacherPersona} user={mockUser} />,
    );

    expect(screen.getByText("Teacher dashboard")).toBeInTheDocument();
    expect(
      screen.getByText("Classroom assessment presets"),
    ).toBeInTheDocument();
    expect(screen.getByText("Homework check")).toBeInTheDocument();
    expect(screen.getByText("Exam revision")).toBeInTheDocument();
  });

  test("navigates to the persona-aware generate page with teacher presets", () => {
    render(
      <TeacherDashboard persona={mockTeacherPersona} user={mockUser} />,
    );

    const homeworkBtn = screen.getByRole("button", {
      name: /Create Homework check/i,
    });
    fireEvent.click(homeworkBtn);
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("/generate?"),
    );
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("persona=teacher"));
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("category=school"));
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("preset=homework-check"),
    );

    const revisionBtn = screen.getByRole("button", {
      name: /Create Exam revision/i,
    });
    fireEvent.click(revisionBtn);
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("preset=exam-revision"),
    );
  });

  test("surfaces class session results with 1-click navigation", () => {
    render(
      <TeacherDashboard persona={mockTeacherPersona} user={mockUser} />,
    );

    const liveResultsBtn = screen.getByRole("button", {
      name: /View live session results/i,
    });
    expect(liveResultsBtn).toBeInTheDocument();
    fireEvent.click(liveResultsBtn);
    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes");

    const allQuizzesBtn = screen.getByRole("button", {
      name: /View homework history/i,
    });
    fireEvent.click(allQuizzesBtn);
    expect(mockPush).toHaveBeenCalledWith("/quiz_history");
  });

  test("uses dynamic school terminology in descriptions", () => {
    render(
      <TeacherDashboard persona={mockTeacherPersona} user={mockUser} />,
    );

    expect(
      screen.getByText((content, element) => {
        return (
          element?.tagName.toLowerCase() === "p" &&
          content.includes("pre-configured for") &&
          content.includes("students")
        );
      }),
    ).toBeInTheDocument();
  });
});
