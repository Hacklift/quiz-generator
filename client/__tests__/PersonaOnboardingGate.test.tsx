import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import PersonaOnboardingGate from "@features/persona/components/PersonaOnboardingGate";

const mockSetPersona = jest.fn();
let mockAuthState: any;
let mockPersonaState: any;
let mockPathname = "/";

jest.mock("next/router", () => ({
  useRouter: () => ({ pathname: mockPathname }),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => mockAuthState,
}));

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => mockPersonaState,
}));

describe("PersonaOnboardingGate", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mockSetPersona.mockReset();
    mockPathname = "/";
    mockAuthState = {
      user: {
        id: "user-1",
        persona_category: null,
        persona_user_type: null,
      },
      isAuthenticated: true,
      isLoading: false,
    };
    mockPersonaState = {
      persona: null,
      source: "none",
      setPersona: mockSetPersona,
    };
  });

  test("shows onboarding when an authenticated user has no persona", () => {
    render(<PersonaOnboardingGate />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Pick your Quizwerk persona")).toBeInTheDocument();
  });

  test("does not show again after the user skips", () => {
    render(<PersonaOnboardingGate />);

    fireEvent.click(
      screen.getByRole("button", { name: /i'll do this later/i }),
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("silently persists a carried persona as inferred", async () => {
    mockSetPersona.mockResolvedValue(undefined);
    mockPersonaState = {
      persona: { category: "school", userType: "teacher" },
      source: "storage",
      setPersona: mockSetPersona,
    };

    render(<PersonaOnboardingGate />);

    await waitFor(() => {
      expect(mockSetPersona).toHaveBeenCalledWith(
        { category: "school", userType: "teacher" },
        { source: "inferred" },
      );
    });
  });

  test("does not show when the profile already has persona", () => {
    mockAuthState.user.persona_category = "corporate";
    mockAuthState.user.persona_user_type = "hr";

    render(<PersonaOnboardingGate />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("does not suppress onboarding on dashboard", () => {
    mockPathname = "/dashboard";

    render(<PersonaOnboardingGate />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  test("suppresses onboarding on auth routes", () => {
    mockPathname = "/auth/login";

    render(<PersonaOnboardingGate />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
