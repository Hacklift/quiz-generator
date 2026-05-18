import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import QuizAnswerField from "../components/home/QuizAnswerField";

describe("QuizAnswerField", () => {
  test("clicking multichoice option text selects the radio option", () => {
    const onAnswerChange = jest.fn();

    render(
      <QuizAnswerField
        questionType="multichoice"
        index={0}
        options={["A) Paris", "B) London"]}
        onAnswerChange={onAnswerChange}
      />,
    );

    fireEvent.click(screen.getByText("Paris"));

    expect(onAnswerChange).toHaveBeenCalledWith(0, "A) Paris");
  });

  test("clicking true-false option text emits numeric values", () => {
    const onAnswerChange = jest.fn();

    render(
      <QuizAnswerField
        questionType="true-false"
        index={1}
        options={[]}
        onAnswerChange={onAnswerChange}
      />,
    );

    fireEvent.click(screen.getByText("true"));

    expect(onAnswerChange).toHaveBeenCalledWith(1, 1);
  });
});
