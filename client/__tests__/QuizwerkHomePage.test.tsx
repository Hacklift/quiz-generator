import React from "react";
import { render, screen } from "@testing-library/react";
import QuizwerkHomePage from "@features/home/QuizwerkHomePage";

const mockRouterPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    isLoading: false,
    user: null,
  }),
}));

jest.mock("@features/profile/api/billingApi", () => ({
  createCheckoutSession: jest.fn(),
  getBillingErrorMessage: jest.fn(() => "Unable to start checkout."),
}));

jest.mock("@features/auth/components/SignInModal", () => ({
  __esModule: true,
  default: () => null,
}));

describe("QuizwerkHomePage", () => {
  beforeEach(() => {
    mockRouterPush.mockClear();
  });

  // Guards the design-system extraction: this snapshot is taken before the
  // Quizwerk primitives move to @shared/ui/quizwerk, so the refactor has to
  // leave the rendered markup byte-identical.
  test("renders the full page markup", () => {
    const { container } = render(<QuizwerkHomePage />);
    expect(container).toMatchSnapshot();
  });

  test("renders every section of the handoff spec", () => {
    render(<QuizwerkHomePage />);

    expect(
      screen.getByRole("heading", { level: 1, name: /Type a topic\./ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Pick the seat you're sitting in")).toBeInTheDocument();
    expect(screen.getByText("Pick a plan that fits how you train")).toBeInTheDocument();
    expect(
      screen.getByText("Built for the room, not the browser tab"),
    ).toBeInTheDocument();
    expect(screen.getByText("The next quiz writes itself.")).toBeInTheDocument();
  });

  test("lists all seven personas", () => {
    render(<QuizwerkHomePage />);

    for (const label of [
      "Teacher",
      "Lecturer",
      "Student",
      "Parent",
      "Business",
      "Employee",
      "HR personnel",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  test("routes to the generate page with persona context", () => {
    render(<QuizwerkHomePage />);

    screen.getByText("Teacher").click();

    expect(mockRouterPush).toHaveBeenCalledTimes(1);
    const href = mockRouterPush.mock.calls[0][0] as string;
    expect(href).toContain("/generate?persona=");
    expect(href).toContain("category=school");
    expect(href).toContain("topic=");
  });
});
