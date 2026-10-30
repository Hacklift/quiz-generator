import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import toast from "react-hot-toast";
import LiveQuizPage from "@features/live-quiz/pages/LiveQuizSessionPage";
import LiveQuizResultsPage from "@features/live-quiz/pages/LiveQuizResultsPage";
import { liveQuizService, type LiveQuizSessionState } from "@features/live-quiz/api/liveQuizService";

let userId: string | null = null;
let authenticated = false;
let authLoading = false;
let orgLoading = false;
let organizationId: string | null = null;
let expire: (() => void) | undefined;
let timerRunning = false;
const listeners = new Map<string, Set<(...args: any[]) => void>>();
const router = {
  replace: jest.fn(),
  query: { completed: "1" },
  events: {
    on: (name: string, callback: (...args: any[]) => void) => { if (!listeners.has(name)) listeners.set(name, new Set()); listeners.get(name)!.add(callback); },
    off: (name: string, callback: (...args: any[]) => void) => { listeners.get(name)?.delete(callback); },
  },
};
function emit(name: string, ...args: any[]) { listeners.get(name)?.forEach((callback) => callback(...args)); }

jest.mock("next/router", () => ({ useRouter: () => router }));
jest.mock("@features/auth/context/authContext", () => ({ useAuth: () => ({
  user: userId ? { id: userId } : null, isAuthenticated: authenticated, isLoading: authLoading,
}) }));
jest.mock("@features/organizations/context/organizationContext", () => ({ useOrganization: () => ({
  scopeKey: `${userId ?? "guest"}:${organizationId ?? "none"}`, isLoading: orgLoading,
  activeOrganization: organizationId ? { organization_id: organizationId } : null,
}) }));
jest.mock("@features/live-quiz/hooks/useLiveQuizTimer", () => ({ useLiveQuizTimer: (
  _expires: string, _now: string, remaining: number, onExpire: () => void, running: boolean,
) => { expire = onExpire; timerRunning = running; return remaining; } }));
jest.mock("react-hot-toast", () => ({ __esModule: true, default: { error: jest.fn() } }));
jest.mock("@features/live-quiz/api/liveQuizService", () => ({ liveQuizService: {
  getSession: jest.fn(), saveAnswer: jest.fn(), submitSession: jest.fn(), markDisconnected: jest.fn(),
} }));
const api = liveQuizService as jest.Mocked<typeof liveQuizService>;

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function state(overrides: Partial<LiveQuizSessionState> = {}): LiveQuizSessionState {
  return {
    session_id: "session-a", quiz_id: "quiz-a", title: "Knowledge check", participant_name: "Learner A",
    started_at: "2035-01-01T10:00:00Z", expires_at: "2035-01-01T10:10:00Z", server_now: "2035-01-01T10:00:00Z",
    status: "active", current_question_index: 0, total_questions: 1, time_limit_minutes: 10, duration_seconds: 600,
    remaining_seconds: 600, question: { question_index: 0, question: "Choose a safe action", options: ["First", "Second"] },
    answers: [], auto_submitted: false, ...overrides,
  };
}

beforeEach(() => {
  jest.resetAllMocks(); listeners.clear();
  userId = null; authenticated = false; authLoading = false; orgLoading = false; organizationId = null;
  timerRunning = false; expire = undefined; router.query = { completed: "1" };
  router.replace.mockResolvedValue(true);
  api.getSession.mockResolvedValue(state());
  api.saveAnswer.mockResolvedValue({ status: "active" });
  api.submitSession.mockResolvedValue({ status: "submitted", score: 1, total_questions: 1, percentage: 100, submitted_at: "2035-01-01T10:01:00Z", auto_submitted: false });
  api.markDisconnected.mockResolvedValue(undefined);
});

test("serializes rapid answer edits and flushes the latest answer before manual submission", async () => {
  const first = deferred<void>();
  const final = deferred<void>();
  api.saveAnswer.mockReturnValueOnce(first.promise).mockReturnValueOnce(final.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByLabelText("First"));
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByLabelText("Second"));
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(api.saveAnswer).toHaveBeenCalledTimes(1);
  expect(api.submitSession).not.toHaveBeenCalled();
  await act(async () => { first.resolve(undefined); });
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(2));
  expect(api.saveAnswer.mock.calls[1]).toEqual(["session-a", 0, "Second", undefined]);
  expect(api.submitSession).not.toHaveBeenCalled();
  await act(async () => { final.resolve(undefined); });
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledWith("session-a", false));
  expect(api.saveAnswer).toHaveBeenCalledTimes(2);
  expect(router.replace).toHaveBeenCalledWith("/live-quiz/session-a/results?completed=1");
});

test("a typing burst behind a deferred save writes only the first edit and final manual answer", async () => {
  const first = deferred<void>();
  const final = deferred<void>();
  api.getSession.mockResolvedValue(state({
    question: { question_index: 0, question: "Explain the rule" },
  }));
  api.saveAnswer.mockReturnValueOnce(first.promise).mockReturnValueOnce(final.promise);
  render(<LiveQuizPage sessionId="session-a" />);

  const input = await screen.findByRole("textbox");
  fireEvent.change(input, { target: { value: "x" } });
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(1));
  for (let length = 2; length <= 40; length += 1) {
    fireEvent.change(input, { target: { value: "x".repeat(length) } });
  }
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(api.saveAnswer).toHaveBeenCalledTimes(1);
  expect(api.submitSession).not.toHaveBeenCalled();

  await act(async () => { first.resolve(undefined); });
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(2));
  expect(api.saveAnswer).toHaveBeenLastCalledWith(
    "session-a", 0, "x".repeat(40), undefined,
  );
  expect(api.submitSession).not.toHaveBeenCalled();

  await act(async () => { final.resolve(undefined); });
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledWith("session-a", false));
  expect(api.saveAnswer).toHaveBeenCalledTimes(2);
});

test("Next coalesces queued typing into the latest answer with its navigation index", async () => {
  const first = deferred<void>();
  const final = deferred<void>();
  api.getSession
    .mockResolvedValueOnce(state({
      total_questions: 2,
      question: { question_index: 0, question: "Explain the rule" },
    }))
    .mockResolvedValue(state({
      total_questions: 2,
      current_question_index: 1,
      question: { question_index: 1, question: "Next question", options: ["A", "B"] },
    }));
  api.saveAnswer.mockReturnValueOnce(first.promise).mockReturnValueOnce(final.promise);
  render(<LiveQuizPage sessionId="session-a" />);

  const input = await screen.findByRole("textbox");
  fireEvent.change(input, { target: { value: "Wear" } });
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(1));
  for (const value of ["Wear ", "Wear g", "Wear gl", "Wear gloves"]) {
    fireEvent.change(input, { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await act(async () => { first.resolve(undefined); });
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(2));
  expect(api.saveAnswer).toHaveBeenLastCalledWith("session-a", 0, "Wear gloves", 1);
  expect(api.getSession).toHaveBeenCalledTimes(1);

  await act(async () => { final.resolve(undefined); });
  await screen.findByText("Next question");
  expect(api.saveAnswer).toHaveBeenCalledTimes(2);
  expect(api.submitSession).not.toHaveBeenCalled();
});

test("a failed final save blocks grading and visibly permits retry", async () => {
  api.saveAnswer.mockRejectedValueOnce({ response: { data: { detail: "Answer save unavailable" } } });
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Submit" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Answer save unavailable"));
  expect(api.submitSession).not.toHaveBeenCalled();
  expect(router.replace).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Submit" })).toBeEnabled();
  expect(timerRunning).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledTimes(1));
});

test("an autosave failure is reported and does not poison a subsequent final save", async () => {
  api.saveAnswer.mockRejectedValueOnce(new Error("network"));
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByLabelText("Second"));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Could not autosave answer. Retry before submitting."));
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledWith("session-a", false));
  expect(api.saveAnswer).toHaveBeenLastCalledWith("session-a", 0, "Second", undefined);
});

test("clearing a text answer is flushed as empty rather than retaining the old answer", async () => {
  api.getSession.mockResolvedValue(state({ question: { question_index: 0, question: "Explain the rule", selected_answer: "Old answer" } }));
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.change(await screen.findByRole("textbox"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalled());
  expect(api.saveAnswer).toHaveBeenLastCalledWith("session-a", 0, "", undefined);
});

test("Next waits for the ordered save before fetching the next question", async () => {
  const saving = deferred<void>();
  api.getSession.mockResolvedValueOnce(state({ total_questions: 2 })).mockResolvedValue(state({ total_questions: 2, current_question_index: 1, question: { question_index: 1, question: "Next question", options: ["A", "B"] } }));
  api.saveAnswer.mockReturnValueOnce(saving.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Next" }));
  expect(api.getSession).toHaveBeenCalledTimes(1);
  await act(async () => { saving.resolve(undefined); });
  await screen.findByText("Next question");
  expect(api.saveAnswer).toHaveBeenCalledWith("session-a", 0, "", 1);
});

test("expiry finalizes without waiting for a hung save or extending the attempt", async () => {
  const saving = deferred<void>();
  api.saveAnswer.mockReturnValueOnce(saving.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByLabelText("First"));
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(1));
  act(() => { expire!(); });
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledWith("session-a", true));
  expect(toast.error).toHaveBeenCalledWith("Time expired. Only answers saved before the deadline can be graded.");
  await act(async () => { saving.resolve(undefined); });
});

test("expiry preempts a hung manual flush and the old operation cannot submit again", async () => {
  const saving = deferred<void>();
  api.saveAnswer.mockReturnValueOnce(saving.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(1));
  expect(timerRunning).toBe(true);
  act(() => { expire!(); });
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledWith("session-a", true));
  await act(async () => { saving.resolve(undefined); });
  expect(api.submitSession).toHaveBeenCalledTimes(1);
  expect(router.replace).toHaveBeenCalledTimes(1);
});

test("an unconfirmed expiry submission offers explicit retry rather than a tight timer retry loop", async () => {
  api.submitSession.mockRejectedValueOnce(new Error("network"));
  render(<LiveQuizPage sessionId="session-a" />);
  await screen.findByRole("button", { name: "Submit" });
  act(() => { expire!(); });
  const retry = await screen.findByRole("button", { name: "Retry submission" });
  expect(timerRunning).toBe(false);
  act(() => { expire!(); });
  expect(api.submitSession).toHaveBeenCalledTimes(1);
  fireEvent.click(retry);
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledTimes(2));
  expect(api.submitSession).toHaveBeenLastCalledWith("session-a", true);
});

test("duplicate manual submit events cannot redirect before the first submission finishes", async () => {
  const submitting = deferred<Awaited<ReturnType<typeof liveQuizService.submitSession>>>();
  api.submitSession.mockReturnValue(submitting.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(router.replace).not.toHaveBeenCalled();
  await act(async () => { submitting.resolve({ status: "submitted", score: 0, total_questions: 1, percentage: 0, submitted_at: "2035-01-01T10:01:00Z", auto_submitted: false }); });
  expect(router.replace).toHaveBeenCalledTimes(1);
});

test("public guest sessions load and submit without an organization membership", async () => {
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByLabelText("First"));
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledWith("session-a", false));
});

test("auth initialization completes before showing session data", async () => {
  authLoading = true;
  const view = render(<LiveQuizPage sessionId="session-a" />);
  expect(api.getSession).not.toHaveBeenCalled();
  authLoading = false;
  view.rerender(<LiveQuizPage sessionId="session-a" />);
  await screen.findByText("Knowledge check");
});

test("a late session response cannot redirect after an account switch", async () => {
  const old = deferred<LiveQuizSessionState>();
  userId = "user-a"; authenticated = true; organizationId = "org-a";
  api.getSession.mockReturnValueOnce(old.promise).mockResolvedValue(state({ title: "New account session" }));
  const view = render(<LiveQuizPage sessionId="session-a" />);
  userId = "user-b";
  view.rerender(<LiveQuizPage sessionId="session-a" />);
  await screen.findByText("New account session");
  await act(async () => { old.resolve(state({ status: "submitted", title: "Old private content" })); });
  expect(router.replace).not.toHaveBeenCalled();
  expect(screen.queryByText("Old private content")).not.toBeInTheDocument();
});

test("an organization switch discards queued saves and stale save failures", async () => {
  const saving = deferred<void>();
  authenticated = true; userId = "user-a"; organizationId = "org-a";
  api.saveAnswer.mockReturnValueOnce(saving.promise);
  const view = render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByLabelText("First"));
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByLabelText("Second"));
  organizationId = "org-b";
  view.rerender(<LiveQuizPage sessionId="session-a" />);
  await screen.findByLabelText("First");
  await act(async () => { saving.reject(new Error("late failure")); });
  expect(api.saveAnswer).toHaveBeenCalledTimes(1);
  expect(toast.error).not.toHaveBeenCalled();
});

test("a submit response after navigation starts cannot hijack the next page", async () => {
  const submitting = deferred<Awaited<ReturnType<typeof liveQuizService.submitSession>>>();
  api.submitSession.mockReturnValue(submitting.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalled());
  act(() => { emit("routeChangeStart", "/dashboard"); });
  await act(async () => { submitting.resolve({ status: "submitted", score: 0, total_questions: 1, percentage: 0, submitted_at: "2035-01-01T10:01:00Z", auto_submitted: false }); });
  expect(router.replace).not.toHaveBeenCalled();
  expect(toast.error).not.toHaveBeenCalled();
});

test("cancelled navigation recovers the page without reviving old submission work", async () => {
  const saving = deferred<void>();
  api.saveAnswer.mockReturnValueOnce(saving.promise);
  render(<LiveQuizPage sessionId="session-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.saveAnswer).toHaveBeenCalled());
  act(() => { emit("routeChangeStart", "/dashboard"); emit("routeChangeError", { cancelled: true }, "/dashboard"); });
  await waitFor(() => expect(api.getSession).toHaveBeenCalledTimes(2));
  expect(await screen.findByRole("button", { name: "Submit" })).toBeEnabled();
  await act(async () => { saving.resolve(undefined); });
  expect(api.submitSession).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  await waitFor(() => expect(api.submitSession).toHaveBeenCalledTimes(1));
});

test("completed navigation between session ids permits the new page to load", async () => {
  const view = render(<LiveQuizPage sessionId="session-a" />);
  await screen.findByLabelText("First");
  act(() => { emit("routeChangeStart", "/live-quiz/session-b"); });
  api.getSession.mockResolvedValue(state({ session_id: "session-b", title: "Second session" }));
  view.rerender(<LiveQuizPage sessionId="session-b" />);
  act(() => { emit("routeChangeComplete", "/live-quiz/session-b"); });
  expect(await screen.findByText("Second session")).toBeInTheDocument();
  expect(api.getSession).toHaveBeenLastCalledWith("session-b");
  expect(timerRunning).toBe(true);
});

test("unmounted session fetches cannot navigate or toast", async () => {
  const loading = deferred<LiveQuizSessionState>();
  api.getSession.mockReturnValue(loading.promise);
  const view = render(<LiveQuizPage sessionId="session-a" />);
  view.unmount();
  await act(async () => { loading.reject(new Error("late network failure")); });
  expect(router.replace).not.toHaveBeenCalled();
  expect(toast.error).not.toHaveBeenCalled();
});

test("authenticated results never show guest signup and use a neutral dashboard return", async () => {
  authenticated = true; userId = "user-a"; organizationId = "org-a";
  api.getSession.mockResolvedValue(state({ status: "submitted", score: 1, percentage: 100 }));
  render(<LiveQuizResultsPage sessionId="session-a" />);
  expect(await screen.findByRole("link", { name: "Back to dashboard" })).toHaveAttribute("href", "/dashboard");
  expect(screen.queryByText("Create your free Quiz Generator account")).not.toBeInTheDocument();
});

test("only an explicit assignment signal changes the authenticated results return link", async () => {
  authenticated = true; userId = "user-a"; organizationId = "org-a";
  api.getSession.mockResolvedValue(state({ status: "submitted", delivery_kind: "quiz" }));
  render(<LiveQuizResultsPage sessionId="session-a" />);
  expect(await screen.findByRole("link", { name: "Back to assigned quizzes" })).toHaveAttribute("href", "/assignments/mine");
});

test("completed guest results preserve the dismissible signup prompt", async () => {
  api.getSession.mockResolvedValue(state({ status: "submitted", score: 1, percentage: 100 }));
  render(<LiveQuizResultsPage sessionId="session-a" />);
  await screen.findByText("Create your free Quiz Generator account");
  fireEvent.click(screen.getByRole("button", { name: "Maybe Later" }));
  expect(screen.queryByText("Create your free Quiz Generator account")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
});

test("guest signup is not rendered while authentication is still resolving", async () => {
  authLoading = true;
  api.getSession.mockResolvedValue(state({ status: "submitted" }));
  const view = render(<LiveQuizResultsPage sessionId="session-a" />);
  expect(api.getSession).not.toHaveBeenCalled();
  expect(screen.queryByText("Create your free Quiz Generator account")).not.toBeInTheDocument();
  authLoading = false; authenticated = true; userId = "user-a";
  view.rerender(<LiveQuizResultsPage sessionId="session-a" />);
  await screen.findByRole("link", { name: "Back to dashboard" });
  expect(screen.queryByText("Create your free Quiz Generator account")).not.toBeInTheDocument();
});

test("late results from a previous workspace cannot replace current results", async () => {
  const old = deferred<LiveQuizSessionState>();
  authenticated = true; userId = "user-a"; organizationId = "org-a";
  api.getSession.mockReturnValueOnce(old.promise).mockResolvedValue(state({ status: "submitted", participant_name: "New workspace participant" }));
  const view = render(<LiveQuizResultsPage sessionId="session-a" />);
  organizationId = "org-b";
  view.rerender(<LiveQuizResultsPage sessionId="session-a" />);
  await screen.findByText("New workspace participant");
  await act(async () => { old.resolve(state({ status: "submitted", participant_name: "Old workspace participant" })); });
  expect(screen.queryByText("Old workspace participant")).not.toBeInTheDocument();
});
