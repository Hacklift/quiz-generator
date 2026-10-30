import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import NavBar from "@features/quiz/components/NavBar";
import SidebarButton from "@features/quiz/components/sidebar/SidebarButton";

const push = jest.fn();
const logout = jest.fn();
let authenticated = true;

jest.mock("next/router", () => ({
  useRouter: () => ({ push, pathname: "/dashboard", asPath: "/dashboard" }),
}));
jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    isAuthenticated: authenticated, isLoading: false, logout,
    user: { username: "A very long username for layout testing" },
  }),
}));
jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({ definition: { label: "Teacher" } }),
}));
jest.mock("@features/persona/hooks/useTerms", () => ({
  useTerms: () => (term: string, form?: string) => {
    if (term === "quiz") return form === "plural" ? "class quizzes" : "class quiz";
    if (term === "group") return form === "plural" ? "classes" : "class";
    return "live class quizzes";
  },
}));
jest.mock("@features/auth/components/SignInModal", () => ({ __esModule: true, default: () => null }));
jest.mock("@features/auth/components/SignUpModal", () => ({ __esModule: true, default: () => null }));
jest.mock("@features/notifications/components/NotificationBell", () => ({
  __esModule: true, default: () => <button>Notifications</button>,
}));
jest.mock("@features/organizations/components/OrganizationSwitcher", () => ({
  __esModule: true, default: () => <select aria-label="Active organization"><option>School</option></select>,
}));
jest.mock("@features/quiz/components/sidebar/UpgradePlanButton", () => ({
  __esModule: true, default: () => <button>Upgrade Plan</button>,
}));
jest.mock("@features/quiz/components/Sidebar", () => ({
  __esModule: true, default: () => <button>Sidebar final action</button>,
}));

beforeEach(() => {
  jest.clearAllMocks();
  authenticated = true;
});

test("keeps closed navigation out of the keyboard order and bounds the desktop sidebar", () => {
  render(<NavBar />);
  expect(screen.queryByRole("complementary", { name: "Workspace navigation" })).not.toBeInTheDocument();
  const toggle = screen.getByRole("button", { name: "Toggle workspace sidebar" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");

  fireEvent.click(toggle);

  const sidebar = screen.getByRole("complementary", { name: "Workspace navigation" });
  expect(sidebar).toHaveClass("top-16", "bottom-0", "overflow-y-auto", "xl:block");
  expect(within(sidebar).getByRole("button", { name: "Sidebar final action" })).toBeInTheDocument();
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(toggle);
  expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
});

test("compact navigation keeps workspace, live and account actions available and closes on navigation", () => {
  render(<NavBar />);
  const toggle = screen.getByRole("button", { name: "Toggle mobile top-nav" });
  expect(toggle).toHaveClass("xl:hidden");
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("link", { name: "Classes & assignments" })).not.toBeInTheDocument();

  fireEvent.click(toggle);

  const cohortLink = screen.getByRole("link", { name: "Classes & assignments" });
  expect(cohortLink).toHaveAttribute("href", "/cohorts");
  expect(screen.getByRole("link", { name: "Live class quizzes" })).toHaveAttribute("href", "/my-live-quizzes");
  expect(screen.getByRole("button", { name: "Upgrade Plan" })).toBeInTheDocument();
  expect(cohortLink.closest("#compact-navigation")).toHaveClass("overflow-y-auto", "xl:hidden");
  fireEvent.click(cohortLink);
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("link", { name: "Classes & assignments" })).not.toBeInTheDocument();
});

test("create action stays compact and routes to generation", () => {
  render(<NavBar />);
  const create = screen.getByRole("button", { name: "Create class quiz" });
  expect(create).toHaveClass("min-h-[44px]", "whitespace-nowrap");
  expect(create).not.toHaveClass("border", "rounded-2xl", "px-6");
  fireEvent.click(create);
  expect(push).toHaveBeenCalledWith("/generate");
  expect(screen.getByTitle(/A very long username/)).toHaveClass("truncate");
});

test("guest compact menu retains authentication actions without private workspace links", () => {
  authenticated = false;
  render(<NavBar />);
  expect(screen.queryByRole("button", { name: "Toggle workspace sidebar" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Toggle mobile top-nav" }));
  expect(screen.getAllByRole("button", { name: "Sign In" })).toHaveLength(2);
  expect(screen.getAllByRole("button", { name: "Sign Up" })).toHaveLength(2);
  expect(screen.queryByRole("link", { name: "Classes & assignments" })).not.toBeInTheDocument();
});

test("sidebar links reuse button styling without losing native link semantics", () => {
  render(<SidebarButton href="/cohorts" icon={<span>Icon</span>} label="Classes & assignments" />);
  const link = screen.getByRole("link", { name: "Icon Classes & assignments" });
  expect(link).toHaveAttribute("href", "/cohorts");
  expect(link).toHaveClass("w-full", "text-sm", "border-l-4");
  expect(screen.getByText("Classes & assignments")).not.toHaveClass("whitespace-nowrap");
});
