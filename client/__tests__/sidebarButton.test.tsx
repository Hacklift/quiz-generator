import React from "react";
import { render, screen } from "@testing-library/react";
import SidebarButton from "../components/home/sidebar/SidebarButton";

describe("SidebarButton", () => {
  test("uses active styling when active", () => {
    render(<SidebarButton label="Saved Quizzes" icon="X" isActive={true} />);

    const button = screen.getByRole("button", { name: /saved quizzes/i });
    expect(button.className).toContain("bg-[#001F3F]");
    expect(button.className).toContain("text-white");
  });

  test("uses inactive styling when not active", () => {
    render(<SidebarButton label="Saved Quizzes" icon="X" isActive={false} />);

    const button = screen.getByRole("button", { name: /saved quizzes/i });
    expect(button.className).toContain("bg-[#E4E4E4]");
    expect(button.className).toContain("text-[#1A1A1A]");
  });
});
