import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import QuestionCard from "@features/live-quiz/components/QuestionCard";

test("live matching question emits a structured answer", () => {
  const onSelect = jest.fn();
  render(
    <QuestionCard
      question={{
        question_index: 0,
        question: "Match countries and capitals",
        question_type: "matching",
        matching_prompts: ["France", "Italy"],
        options: ["Paris", "Rome"],
      }}
      selectedAnswer={{ France: "", Italy: "" }}
      onSelect={onSelect}
    />,
  );

  fireEvent.change(screen.getAllByRole("combobox")[0], {
    target: { value: "Paris" },
  });
  expect(onSelect).toHaveBeenCalledWith({ France: "Paris", Italy: "" });
});
