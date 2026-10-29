import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import RequireTrainingManager, {
  canManageTrainingRuns, canReadTrainingReports,
} from "@features/training/components/RequireTrainingManager";

const replace = jest.fn();
let authState: any;
let organizationState: any;

jest.mock("next/router", () => ({ useRouter: () => ({ replace }) }));
jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true, default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@features/auth/context/authContext", () => ({ useAuth: () => authState }));
jest.mock("@features/organizations/context/organizationContext", () => ({
  useOrganization: () => organizationState,
}));

beforeEach(() => {
  replace.mockReset();
  authState = {
    isAuthenticated: true, isLoading: false,
    user: { persona_category: "corporate", persona_user_type: "employee" },
  };
  organizationState = { activeOrganization: { role: "owner" }, isLoading: false };
});

test.each(["owner", "admin", "facilitator"])("allows %s management independent of persona", (role) => {
  expect(canManageTrainingRuns(role)).toBe(true);
  organizationState.activeOrganization.role = role;
  render(<RequireTrainingManager><p>Training run content</p></RequireTrainingManager>);
  expect(screen.getByText("Training run content")).toBeInTheDocument();
});

test.each(["learner", "author", "guardian", "auditor", null])("denies management for %s", async (role) => {
  authState.user = { persona_category: "corporate", persona_user_type: "hr" };
  organizationState.activeOrganization = role ? { role } : null;
  expect(canManageTrainingRuns(role)).toBe(false);
  render(<RequireTrainingManager><p>Training run content</p></RequireTrainingManager>);
  expect(screen.queryByText("Training run content")).not.toBeInTheDocument();
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
});

test("allows auditors to read reports but not manage runs", () => {
  organizationState.activeOrganization.role = "auditor";
  expect(canReadTrainingReports("auditor")).toBe(true);
  render(<RequireTrainingManager access="report"><p>Report content</p></RequireTrainingManager>);
  expect(screen.getByText("Report content")).toBeInTheDocument();
});

test("waits for proven membership before rendering or redirecting", () => {
  organizationState = { activeOrganization: null, isLoading: true };
  const view = render(<RequireTrainingManager><p>Training run content</p></RequireTrainingManager>);
  expect(screen.queryByText("Training run content")).not.toBeInTheDocument();
  expect(replace).not.toHaveBeenCalled();
  organizationState = { activeOrganization: { role: "admin" }, isLoading: false };
  view.rerender(<RequireTrainingManager><p>Training run content</p></RequireTrainingManager>);
  expect(screen.getByText("Training run content")).toBeInTheDocument();
});
