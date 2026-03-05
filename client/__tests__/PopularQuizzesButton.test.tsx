import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import PopularQuizzesButton from "../components/home/sidebar/PopularQuizzesButton";

const push = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/home",
}));

describe("PopularQuizzesButton", () => {
  beforeEach(() => {
    push.mockClear();
  });

  test("routes to /popular on click", () => {
    render(<PopularQuizzesButton />);
    fireEvent.click(screen.getByRole("button", { name: /Popular Quizzes/i }));
    expect(push).toHaveBeenCalledWith("/popular");
  });
});
