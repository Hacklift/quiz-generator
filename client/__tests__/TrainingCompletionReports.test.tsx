import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import toast from "react-hot-toast";
import TrainingRunDetailPage from "@features/training/pages/TrainingRunDetailPage";
import TrainingRunsPage from "@features/training/pages/TrainingRunsPage";
import { trainingRunApi, type TrainingRunDetail } from "@features/training/api/trainingRunApi";

const router = { push: jest.fn(), replace: jest.fn(), isReady: true, query: { kind: "compliance" } };
jest.mock("next/router", () => ({ useRouter: () => router }));
jest.mock("@features/training/components/RequireTrainingManager", () => ({
  __esModule: true, default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@features/quiz/components/NavBar", () => ({ __esModule: true, default: () => null }));
jest.mock("@features/quiz/components/Footer", () => ({ __esModule: true, default: () => null }));
jest.mock("react-hot-toast", () => ({ __esModule: true, default: { success: jest.fn(), error: jest.fn() } }));
jest.mock("@features/training/api/trainingRunApi", () => ({ trainingRunApi: {
  getRun: jest.fn(), listOwnedQuizzes: jest.fn(), listRuns: jest.fn(),
  createRun: jest.fn(), closeRun: jest.fn(), downloadCompletionReport: jest.fn(),
} }));
const api = trainingRunApi as jest.Mocked<typeof trainingRunApi>;

const detail = (): TrainingRunDetail => ({
  id: "run-1", quiz_id: "quiz-1", title: "Safety training", kind: "compliance", purpose: "health_and_safety",
  status: "open", access_mode: "assigned_only", time_limit_minutes: 20, passing_threshold_percentage: 80,
  created_at: "2026-10-19T10:00:00Z", closes_at: "2026-11-19T10:00:00Z",
  assigned_count: 2, started_count: 1, completed_count: 1, report_is_final: false,
  completion_register: [{
    assignment_id: "assignment-1", recipient_email: "learner@example.com", status: "completed",
    completed_at: "2026-10-19T12:00:00Z", latest_score: 4, latest_percentage: 80,
    attempts_used: 1, max_attempts: 2, outcome: "passed",
  }, {
    assignment_id: "assignment-2", recipient_email: "absent@example.com", status: "assigned",
    attempts_used: 0, max_attempts: 2, outcome: "not_completed",
  }],
});

beforeEach(() => {
  jest.clearAllMocks();
  api.getRun.mockResolvedValue(detail());
  api.listOwnedQuizzes.mockResolvedValue([{ id: "quiz-1", title: "Safety quiz", quiz_type: "multichoice" }]);
  api.listRuns.mockResolvedValue([]);
  api.createRun.mockResolvedValue(detail());
  api.downloadCompletionReport.mockResolvedValue(new Blob(["CSV"]));
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: jest.fn(() => "blob:report") });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: jest.fn() });
  Object.defineProperty(crypto, "randomUUID", { configurable: true, value: jest.fn(() => "creation-key") });
  jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
});

afterEach(() => { jest.restoreAllMocks(); });

test("shows the per-run assignee report, outcome, threshold and non-starter", async () => {
  render(<TrainingRunDetailPage runId="run-1" />);
  await screen.findByText("Safety training");
  expect(screen.getByRole("status")).toHaveTextContent("Provisional");
  const completed = screen.getByText("learner@example.com").closest("tr")!;
  expect(within(completed).getByText("4 (80%)")).toBeInTheDocument();
  expect(within(completed).getByText("Passed")).toBeInTheDocument();
  const absent = screen.getByText("absent@example.com").closest("tr")!;
  expect(within(absent).getByText("Not started")).toBeInTheDocument();
  expect(within(absent).getByText("Not completed")).toBeInTheDocument();
  expect(screen.getByText("Passing threshold")).toBeInTheDocument();
});

test("one click exports the selected run and releases the download object URL", async () => {
  render(<TrainingRunDetailPage runId="run-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "Export completion CSV" }));
  await waitFor(() => expect(api.downloadCompletionReport).toHaveBeenCalledWith("run-1"));
  await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:report"));
  expect(toast.success).toHaveBeenCalledWith("Completion report downloaded.");
});

test("download failures show feedback rather than success", async () => {
  api.downloadCompletionReport.mockRejectedValue(new Error("network"));
  render(<TrainingRunDetailPage runId="run-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "Export completion CSV" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Could not export the completion report. Please try again."));
  expect(toast.success).not.toHaveBeenCalled();
});

test("oversized exports explain the limit instead of implying a successful partial download", async () => {
  api.downloadCompletionReport.mockRejectedValue({ response: { status: 413 } });
  render(<TrainingRunDetailPage runId="run-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "Export completion CSV" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith(
    "This run exceeds the interactive report limit. Contact support for a complete export.",
  ));
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});

test("unavailable audit evidence is distinguished from transient export failures", async () => {
  api.downloadCompletionReport.mockRejectedValue({ response: { status: 503, data: new Blob(["error"]) } });
  render(<TrainingRunDetailPage runId="run-1" />);
  fireEvent.click(await screen.findByRole("button", { name: "Export completion CSV" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith(
    "Completion evidence is unavailable. Contact support; no CSV was generated.",
  ));
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});

test("a large register keeps management available and uses complete counts in close confirmation", async () => {
  const run = detail();
  run.register_availability = "limit_exceeded";
  run.participant_count = 10002;
  run.assigned_count = 0;
  run.completed_count = 10000;
  run.completion_register = [];
  api.getRun.mockResolvedValueOnce(run).mockResolvedValue({ ...run, status: "closed", report_is_final: true });
  api.closeRun.mockResolvedValue({ ...run, status: "closed" });
  render(<TrainingRunDetailPage runId="run-1" />);
  expect(await screen.findByRole("note")).toHaveTextContent("run management remain available");
  expect(screen.getByRole("button", { name: "Export completion CSV" })).toBeDisabled();
  expect(screen.queryByText("No participants have started this run.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Close run" }));
  const dialog = screen.getByRole("dialog");
  expect(dialog).toHaveTextContent("2 participants are not completed.");
  fireEvent.click(within(dialog).getByRole("button", { name: "Close run permanently" }));
  await waitFor(() => expect(api.closeRun).toHaveBeenCalledWith("run-1"));
  await waitFor(() => expect(screen.queryByRole("button", { name: "Close run" })).toBeNull());
});

test("closed records are clearly final while legacy thresholds remain unknown", async () => {
  const run = detail();
  run.status = "closed";
  run.report_is_final = true;
  run.report_finalized_at = "2026-10-19T13:00:00Z";
  run.passing_threshold_percentage = null;
  run.completion_register[0].outcome = "unknown";
  api.getRun.mockResolvedValue(run);
  render(<TrainingRunDetailPage runId="run-1" />);
  await screen.findByText("Safety training");
  expect(screen.getByRole("status")).toHaveTextContent("Final audit record");
  expect(screen.getByText(/No passing threshold was recorded/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Close run" })).toBeNull();
  expect(screen.queryByText("Passed")).toBeNull();
});

test("creation submits the configured threshold on the existing training API", async () => {
  render(<TrainingRunsPage />);
  await screen.findByRole("option", { name: "Safety quiz" });
  const select = screen.getByRole("option", { name: "Safety quiz" }).closest("select")!;
  fireEvent.change(select, { target: { value: "quiz-1" } });
  fireEvent.change(screen.getByLabelText("Recipients"), { target: { value: "learner@example.com" } });
  const threshold = screen.getByLabelText("Passing threshold (%)");
  expect(threshold).toHaveValue(80);
  fireEvent.change(threshold, { target: { value: "70" } });
  fireEvent.click(screen.getByRole("button", { name: "Create training run" }));
  await waitFor(() => expect(api.createRun).toHaveBeenCalledWith(
    expect.objectContaining({ passing_threshold_percentage: 70, kind: "compliance" }), "creation-key",
  ));
});

test("the run list does not present unavailable final evidence as zero completion", async () => {
  api.listRuns.mockResolvedValue([{ ...detail(), status: "closed", summary_availability: "unavailable" }]);
  render(<TrainingRunsPage />);
  expect(await screen.findByText("Final evidence unavailable")).toBeInTheDocument();
  expect(screen.queryByText("0 completed")).toBeNull();
});
