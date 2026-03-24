import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import NavBar from "../components/home/NavBar";

const mockUseAuth = jest.fn();
const logout = jest.fn();

jest.mock("../contexts/authContext", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
    ...props
  }: React.PropsWithChildren<{ href: string }>) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  };
});

jest.mock("../components/home/QuizDropdown", () => () => (
  <div>QuizDropdown</div>
));
jest.mock("../components/home/PricingLink", () => () => <div>Pricing</div>);
jest.mock("../components/home/HowItWorksLink", () => () => (
  <div>HowItWorks</div>
));
jest.mock("../components/home/NavGenerateQuizButton", () => () => (
  <button>Generate</button>
));
jest.mock(
  "../components/home/Sidebar",
  () =>
    ({ onBrowseClick }: { onBrowseClick: () => void }) => (
      <button onClick={onBrowseClick}>Open Browse</button>
    ),
);
jest.mock(
  "../components/home/modals/BrowseModal",
  () =>
    ({ isOpen }: { isOpen: boolean }) =>
      isOpen ? <div data-testid="browse-modal" /> : null,
);
jest.mock(
  "../components/auth/SignInModal",
  () =>
    ({ isOpen }: { isOpen: boolean }) =>
      isOpen ? <div data-testid="signin-modal" /> : null,
);
jest.mock(
  "../components/auth/SignUpModal",
  () =>
    ({ isOpen }: { isOpen: boolean }) =>
      isOpen ? <div data-testid="signup-modal" /> : null,
);

describe("NavBar", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("shows auth buttons for unauthenticated users", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      logout,
      isLoading: false,
    });

    render(<NavBar />);

    expect(
      screen.getAllByRole("button", { name: /sign in/i }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("button", { name: /sign up/i }).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByText(/hi,/i)).not.toBeInTheDocument();
  });

  test("shows greeting and logout for authenticated users", () => {
    mockUseAuth.mockReturnValue({
      user: { username: "Ada" },
      isAuthenticated: true,
      logout,
      isLoading: false,
    });

    render(<NavBar />);

    expect(screen.getAllByText(/hi, ada/i).length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole("button", { name: /logout/i })[0]);
    expect(logout).toHaveBeenCalled();
  });
});
