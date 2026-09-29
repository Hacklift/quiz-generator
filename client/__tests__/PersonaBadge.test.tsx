import React from "react";
import { render, screen } from "@testing-library/react";
import PersonaBadge from "@features/persona/components/PersonaBadge";

describe("PersonaBadge", () => {
  test("renders role label and default chips for Teacher", () => {
    render(<PersonaBadge userType="teacher" />);

    expect(screen.getByText("Set up for: Teacher")).toBeInTheDocument();
    expect(screen.getByText("Persona defaults applied")).toBeInTheDocument();
    expect(screen.getByText("Students")).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("Multiple Choice")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("Guidance:")).toBeInTheDocument();
    expect(screen.getByText("Applied")).toBeInTheDocument();
  });

  test("renders role label and default chips for Parent (Easy, Children)", () => {
    render(<PersonaBadge userType="parent" />);

    expect(screen.getByText("Set up for: Parent")).toBeInTheDocument();
    expect(screen.getByText("Children")).toBeInTheDocument();
    expect(screen.getByText("Easy")).toBeInTheDocument();
  });

  test("renders role label and default chips for HR (Employees)", () => {
    render(<PersonaBadge userType="hr" />);

    expect(screen.getByText("Set up for: HR personnel")).toBeInTheDocument();
    expect(screen.getByText("Employees")).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();
  });

  test("hides default chips when showDefaults is false", () => {
    render(<PersonaBadge userType="student" showDefaults={false} />);

    expect(screen.getByText("Set up for: Student")).toBeInTheDocument();
    expect(screen.queryByTestId("persona-badge-defaults")).not.toBeInTheDocument();
  });

  test("shows live applied defaults when form values override taxonomy defaults", () => {
    render(
      <PersonaBadge
        userType="teacher"
        appliedDefaults={{
          audienceType: "exam candidates",
          difficultyLevel: "hard",
          numQuestions: 6,
          questionType: "short-answer",
        }}
      />,
    );

    expect(screen.getByText("Exam candidates")).toBeInTheDocument();
    expect(screen.getByText("Hard")).toBeInTheDocument();
    expect(screen.getByText("Short Answer")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
  });

  test("uses audience fallback when the live audience value is empty", () => {
    render(
      <PersonaBadge
        userType="teacher"
        audienceFallback="students"
        appliedDefaults={{
          audienceType: "",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        }}
      />,
    );

    expect(screen.getByText("Students")).toBeInTheDocument();
  });
});
