import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import SignInButton from "../components/home/SignInButton";

describe("SignInButton", () => {
  it("renders the sign-in button", () => {
    render(<SignInButton onOpen={jest.fn()} />);
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("calls onOpen when clicked", () => {
    const onOpen = jest.fn();
    render(<SignInButton onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(onOpen).toHaveBeenCalled();
  });
});
