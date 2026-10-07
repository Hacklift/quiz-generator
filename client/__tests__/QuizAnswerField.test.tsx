import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import QuizAnswerField from "@features/quiz/components/QuizAnswerField";

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

  test("matching emits a structured mapping", () => {
    const onAnswerChange = jest.fn();
    render(
      <QuizAnswerField
        questionType="matching"
        index={2}
        options={["Paris", "Rome"]}
        value={{ France: "", Italy: "" }}
        onAnswerChange={onAnswerChange}
      />,
    );

    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "Paris" } });
    expect(onAnswerChange).toHaveBeenCalledWith(2, { France: "Paris", Italy: "" });
  });
});
