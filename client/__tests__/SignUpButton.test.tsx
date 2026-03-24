import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import SignUpButton from "../components/home/SignUpButton";

describe("SignUpButton", () => {
  it("renders the sign-up button", () => {
    render(<SignUpButton onOpen={jest.fn()} />);
    expect(
      screen.getByRole("button", { name: /sign up/i }),
    ).toBeInTheDocument();
  });

  it("calls the open handler when clicked", () => {
    const onOpen = jest.fn();
    render(<SignUpButton onOpen={onOpen} />);

    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));

    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
