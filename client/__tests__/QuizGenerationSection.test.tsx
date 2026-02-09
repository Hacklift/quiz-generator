import React, { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import QuizGenerationSection from "../components/home/QuizGenerationSection";

const Wrapper = () => {
  const [profession, setProfession] = useState("");
  const [audienceType, setAudienceType] = useState("");
  const [customInstruction, setCustomInstruction] = useState("");
  const [numQuestions, setNumQuestions] = useState(1);
  const [questionType, setQuestionType] = useState("multichoice");
  const [difficultyLevel, setDifficultyLevel] = useState("easy");
  const [token, setToken] = useState("");

  return (
    <QuizGenerationSection
      profession={profession}
      setProfession={setProfession}
      audienceType={audienceType}
      setAudienceType={setAudienceType}
      customInstruction={customInstruction}
      setCustomInstruction={setCustomInstruction}
      numQuestions={numQuestions}
      setNumQuestions={setNumQuestions}
      questionType={questionType}
      setQuestionType={setQuestionType}
      difficultyLevel={difficultyLevel}
      setDifficultyLevel={setDifficultyLevel}
      token={token}
      setToken={setToken}
      previousToken=""
    />
  );
};

describe("QuizGenerationSection", () => {
  test("difficulty dropdown opens and selects option", () => {
    render(<Wrapper />);

    const trigger = screen.getByRole("button", { name: /easy/i });
    fireEvent.click(trigger);

    const mediumOption = screen.getByRole("option", { name: /medium/i });
    fireEvent.click(mediumOption);

    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
  });

  test("difficulty dropdown closes on outside click", () => {
    render(<Wrapper />);

    const trigger = screen.getByRole("button", { name: /easy/i });
    fireEvent.click(trigger);

    expect(screen.getByRole("option", { name: /easy/i })).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    expect(
      screen.queryByRole("option", { name: /easy/i }),
    ).not.toBeInTheDocument();
  });
});
