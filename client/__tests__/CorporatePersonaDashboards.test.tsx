import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import BusinessDashboard from "@features/dashboard/corporate/views/BusinessDashboard";
import EmployeeDashboard from "@features/dashboard/corporate/views/EmployeeDashboard";
import HrDashboard from "@features/dashboard/corporate/views/HrDashboard";
import { I18nextProvider } from "react-i18next";
import { createLocaleI18n } from "@features/locale/i18n";

const push = jest.fn();
const listRuns = jest.fn();
const listMyAssignments = jest.fn();
const startAssignment = jest.fn();
const toastError = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push, query: {}, pathname: "/dashboard" }),
}));

jest.mock("@features/persona/hooks/useTerms", () => ({
  useTerms: () => (key: string, form?: string) => {
    const terms: Record<string, string> = {
      quiz: "training quiz",
      group: form === "plural" ? "teams" : "team",
      session: "training session",
    };
    return terms[key] || key;
  },
}));

jest.mock("@features/training/api/trainingRunApi", () => ({
  trainingRunApi: {
    listRuns: (...args: unknown[]) => listRuns(...args),
    listMyAssignments: (...args: unknown[]) => listMyAssignments(...args),
    startAssignment: (...args: unknown[]) => startAssignment(...args),
  },
}));

jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  saveParticipantToken: jest.fn(),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { error: (...args: unknown[]) => toastError(...args) },
}));

const user = {
  id: "u1",
  username: "casey",
  email: "casey@example.com",
  is_verified: true,
};

describe("Corporate persona dashboards", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    listRuns.mockResolvedValue([]);
    listMyAssignments.mockResolvedValue([]);
  });

  test("Business presents onboarding and product-knowledge presets", async () => {
    render(
      <BusinessDashboard
        persona={{ category: "corporate", userType: "business" }}
        user={user}
      />,
    );

    await waitFor(() => expect(listRuns).toHaveBeenCalled());
    expect(screen.getByText("Employee onboarding")).toBeInTheDocument();
    expect(screen.getByText("Product knowledge")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Manage training runs" }),
    );
    expect(push).toHaveBeenCalledWith("/training-runs?kind=business");
  });

  test("Employee makes an assigned training item actionable", async () => {
    listMyAssignments.mockResolvedValue([
      {
        id: "assignment-1",
        title: "Security basics",
        status: "assigned",
        due_at: null,
        is_overdue: false,
        attempts_used: 0,
        can_retry: true,
      },
    ]);
    startAssignment.mockResolvedValue({
      session_id: "session-1",
      participant_token: "token",
      redirect_url: "/live-quiz/session-1",
    });
    render(
      <EmployeeDashboard
        persona={{ category: "corporate", userType: "employee" }}
        user={user}
      />,
    );

    expect(await screen.findByText("Security basics")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start training" }));
    await waitFor(() =>
      expect(startAssignment).toHaveBeenCalledWith("assignment-1"),
    );
  });

  test("Employee receives feedback when an assigned training cannot start", async () => {
    listMyAssignments.mockResolvedValue([
      {
        id: "assignment-1",
        title: "Security basics",
        status: "assigned",
        due_at: null,
        is_overdue: false,
        attempts_used: 0,
        can_retry: true,
      },
    ]);
    startAssignment.mockRejectedValue({
      response: { data: { detail: "Training run is closed" } },
    });
    render(
      <EmployeeDashboard
        persona={{ category: "corporate", userType: "employee" }}
        user={user}
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Start training" }),
    );

    await waitFor(() =>
      expect(toastError).toHaveBeenCalledWith("Training run is closed"),
    );
  });

  test.each([
    ["es", "Sin fecha límite"],
    ["fr", "Aucune date limite"],
  ])(
    "%s translates assignment status without a translation API",
    async (locale, label) => {
      listMyAssignments.mockResolvedValue([
        {
          id: "assignment-1",
          title: "Security basics",
          status: "assigned",
          due_at: null,
          is_overdue: false,
          attempts_used: 0,
          can_retry: true,
        },
      ]);
      const i18n = createLocaleI18n();
      await i18n.changeLanguage(locale);
      render(
        <I18nextProvider i18n={i18n}>
          <EmployeeDashboard
            persona={{ category: "corporate", userType: "employee" }}
            user={user}
          />
        </I18nextProvider>,
      );
      expect(await screen.findByText(new RegExp(label))).toBeInTheDocument();
      expect(screen.queryByText(/No due date/)).not.toBeInTheDocument();
    },
  );

  test("HR presents compliance presets and completion-register entry", async () => {
    render(
      <HrDashboard
        persona={{ category: "corporate", userType: "hr" }}
        user={user}
      />,
    );

    await waitFor(() => expect(listRuns).toHaveBeenCalled());
    expect(screen.getByText("Harassment prevention")).toBeInTheDocument();
    expect(screen.getByText("Health & safety")).toBeInTheDocument();
    expect(screen.getByText("Completion register")).toBeInTheDocument();
  });
});
