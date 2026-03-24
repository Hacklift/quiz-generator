import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import SignInButton from "../components/home/SignInButton";

describe("SignInButton", () => {
  it("renders the sign-in button", () => {
    render(<SignInButton onOpen={jest.fn()} />);
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("calls the open handler when clicked", () => {
    const onOpen = jest.fn();
    render(<SignInButton onOpen={onOpen} />);

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
