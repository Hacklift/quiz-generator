import React from "react";
import { render, screen } from "@testing-library/react";
import DashboardPage from "@features/dashboard/pages/DashboardPage";
import type { Persona, PersonaUserType } from "@shared/config/persona";

const mockUser = {
  id: "u1",
  username: "casey",
  email: "casey@example.com",
  is_verified: true,
  full_name: "Casey Jones",
};

let mockPersona: Persona | null = null;

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn(), pathname: "/dashboard", query: {} }),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({ persona: mockPersona, isLoading: false }),
}));

jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => <nav>NavBar</nav>,
}));

jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => <footer>Footer</footer>,
}));

jest.mock("@features/dashboard/components/RecentQuizzes", () => ({
  __esModule: true,
  default: ({ heading }: { heading: string }) => <section>{heading}</section>,
}));

jest.mock("@features/persona/components/PersonaPicker", () => ({
  __esModule: true,
  default: () => <div>persona-picker</div>,
}));

describe("DashboardPage dispatch", () => {
  afterEach(() => {
    mockPersona = null;
  });

  test("shows the persona picker when no persona is set", () => {
    mockPersona = null;
    render(<DashboardPage />);
    expect(screen.getByText("persona-picker")).toBeInTheDocument();
  });

  // Every user type must reach its own view — this is what stops a new
  // persona from silently falling through to a blank dashboard.
  const CASES: [PersonaUserType, string][] = [
    ["teacher", "Teacher dashboard"],
    ["lecturer", "Lecturer dashboard"],
    ["student", "Student dashboard"],
    ["parent", "Parent dashboard"],
    ["business", "Business dashboard"],
    ["employee", "Employee dashboard"],
    ["hr", "HR personnel dashboard"],
  ];

  test.each(CASES)("routes %s to its view", (userType, heading) => {
    mockPersona = {
      category: ["teacher", "lecturer", "student", "parent"].includes(userType)
        ? "school"
        : "corporate",
      userType,
    };

    render(<DashboardPage />);

    expect(screen.getByText(heading)).toBeInTheDocument();
  });

  test("school dashboard greets the user and uses school terminology", () => {
    mockPersona = { category: "school", userType: "teacher" };

    render(<DashboardPage />);

    expect(screen.getByText("Welcome back, Casey")).toBeInTheDocument();
    expect(screen.getByText(/New homework/)).toBeInTheDocument();
  });
});
