import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import RequireTrainingManager, {
  canManageTrainingRuns,
} from "@features/training/components/RequireTrainingManager";

const replace = jest.fn();
let authState: any;

jest.mock("next/router", () => ({
  useRouter: () => ({ replace }),
}));

jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => authState,
}));

describe("RequireTrainingManager", () => {
  beforeEach(() => {
    replace.mockReset();
    authState = {
      isAuthenticated: true,
      isLoading: false,
      user: { persona_category: "corporate", persona_user_type: "business" },
    };
  });

  test("allows the corporate business and HR manager personas", () => {
    expect(canManageTrainingRuns("corporate", "business")).toBe(true);
    expect(canManageTrainingRuns("corporate", "hr")).toBe(true);
  });

  test("does not treat employee or school personas as training managers", () => {
    expect(canManageTrainingRuns("corporate", "employee")).toBe(false);
    expect(canManageTrainingRuns("school", "teacher")).toBe(false);
    expect(canManageTrainingRuns(null, null)).toBe(false);
  });

  test("redirects a non-manager before protected page content mounts", async () => {
    authState = {
      isAuthenticated: true,
      isLoading: false,
      user: { persona_category: "corporate", persona_user_type: "employee" },
    };

    render(
      <RequireTrainingManager>
        <p>Training run content</p>
      </RequireTrainingManager>,
    );

    expect(screen.queryByText("Training run content")).not.toBeInTheDocument();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  test("does not authorize a management page from a URL or guest persona hint", () => {
    authState = {
      isAuthenticated: true,
      isLoading: false,
      user: { persona_category: null, persona_user_type: null },
    };

    render(
      <RequireTrainingManager>
        <p>Training run content</p>
      </RequireTrainingManager>,
    );

    expect(screen.queryByText("Training run content")).not.toBeInTheDocument();
  });
});
