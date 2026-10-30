import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import toast from "react-hot-toast";
import CohortsPage from "@features/cohorts/pages/CohortsPage";
import CohortDetailPage from "@features/cohorts/pages/CohortDetailPage";
import AssignmentsPage from "@features/cohorts/pages/AssignmentsPage";
import AssignmentDetailPage from "@features/cohorts/pages/AssignmentDetailPage";
import MyAssignmentsPage from "@features/cohorts/pages/MyAssignmentsPage";
import AssignedAttemptPage from "@features/cohorts/pages/AssignedAttemptPage";
import { cohortDeliveryApi, type Assignment, type Cohort } from "@features/cohorts/api/cohortDeliveryApi";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";

let role = "owner";
let orgId = "org-a";
let userId = "user-a";
let scopeLoading = false;
let authenticated = true;
const router = { push: jest.fn(), isReady: true, query: {} as { cohort?: string } };
jest.mock("next/router", () => ({ useRouter: () => router }));
jest.mock("@features/auth/context/authContext", () => ({ useAuth: () => ({ user: { id: userId }, isAuthenticated: authenticated }) }));
jest.mock("@features/auth/components/RequireAuth", () => ({ __esModule: true, default: ({ children }: { children: React.ReactNode }) => authenticated ? <>{children}</> : <p>Sign in</p> }));
jest.mock("@features/organizations/context/organizationContext", () => ({ useOrganization: () => ({
  scopeKey: `${userId}:${orgId}`, isLoading: scopeLoading,
  activeOrganization: { organization_id: orgId, organization_name: "Demo workspace", role },
}) }));
jest.mock("@features/persona/hooks/useTerms", () => ({ useTerms: () => (term: string, form?: string) => term === "group" ? form === "plural" ? "classes" : "class" : form === "plural" ? "quizzes" : "quiz" }));
jest.mock("@features/quiz/components/NavBar", () => ({ __esModule: true, default: () => null }));
jest.mock("@features/quiz/components/Footer", () => ({ __esModule: true, default: () => null }));
jest.mock("react-hot-toast", () => ({ __esModule: true, default: { error: jest.fn(), success: jest.fn() } }));
jest.mock("@features/live-quiz/api/liveQuizService", () => ({ saveParticipantToken: jest.fn() }));
jest.mock("@features/cohorts/api/cohortDeliveryApi", () => ({ cohortDeliveryApi: {
  listCohorts: jest.fn(), getCohort: jest.fn(), createCohort: jest.fn(), updateCohort: jest.fn(), archiveCohort: jest.fn(),
  listMembers: jest.fn(), memberOptions: jest.fn(), recipientOptions: jest.fn(), setMember: jest.fn(), removeMember: jest.fn(), progress: jest.fn(),
  listAssignments: jest.fn(), myAssignments: jest.fn(), quizzes: jest.fn(), getAssignment: jest.fn(), createAssignment: jest.fn(),
  startAssignment: jest.fn(), closeAssignment: jest.fn(), attempts: jest.fn(), attempt: jest.fn(),
} }));
const api = cohortDeliveryApi as jest.Mocked<typeof cohortDeliveryApi>;
const cohort: Cohort = { id: "cohort-a", organization_id: "org-a", kind: "class", name: "Alpha class", parent_cohort_id: null, status: "active", can_manage: true, can_assign: true, can_report: true };
const assignment: Assignment = {
  id: "assignment-a", title: "Safety knowledge", quiz_id: "quiz-a", quiz_revision_id: "revision-a", cohort_id: "cohort-a",
  status: "open", closes_at: "2035-10-30T12:00:00Z", time_limit_minutes: 20, max_attempts: 2,
  passing_threshold_percentage: 80, can_manage: true, can_report: true, participant_count: 2, completed_count: 1,
  outstanding_count: 1, average_percentage: 75, recipients: [{
    recipient_id: "recipient-a", user_id: "user-b", recipient_name: "Learner B", recipient_status: "completed",
    has_completed: true, can_start: false, available: true, max_attempts: 2, attempts_used: 1, latest_percentage: 75,
  }],
};
const empty = { items: [], next_cursor: null };
beforeEach(() => {
  jest.resetAllMocks(); role = "owner"; orgId = "org-a"; userId = "user-a"; scopeLoading = false; authenticated = true;
  router.query = {};
  api.listCohorts.mockResolvedValue({ items: [cohort], next_cursor: null });
  api.getCohort.mockResolvedValue(cohort);
  api.listMembers.mockResolvedValue(empty);
  api.memberOptions.mockResolvedValue({ items: [{ user_id: "user-b", name: "Learner B" }], next_cursor: null });
  api.recipientOptions.mockResolvedValue({ items: [{ user_id: "user-b", name: "Learner B" }], next_cursor: null });
  api.progress.mockResolvedValue({ items: [{ id: "assignment-a", title: "Safety knowledge", participant_count: 2, completed_count: 1, outstanding_count: 1, completion_percentage: 50, average_percentage: 75 }], next_cursor: null });
  api.listAssignments.mockResolvedValue(empty);
  api.myAssignments.mockResolvedValue({ items: [{ ...assignment, can_start: true, recipient_status: "assigned" }], next_cursor: null });
  api.quizzes.mockResolvedValue({ items: [{ id: "quiz-a", title: "Quiz one" }], next_cursor: null });
  api.getAssignment.mockResolvedValue(assignment);
  api.createAssignment.mockResolvedValue(assignment);
  api.attempts.mockResolvedValue(empty);
  Object.defineProperty(crypto, "randomUUID", { configurable: true, value: jest.fn().mockReturnValueOnce("key-1").mockReturnValueOnce("key-2").mockReturnValueOnce("key-3") });
});

test("waits for authenticated organization resolution before any scoped request", () => {
  scopeLoading = true;
  const view = render(<CohortsPage />);
  expect(api.listCohorts).not.toHaveBeenCalled();
  scopeLoading = false; authenticated = false;
  view.rerender(<CohortsPage />);
  expect(api.listCohorts).not.toHaveBeenCalled();
});

test("discarding a stale organization response never displays the previous roster", async () => {
  let resolveOld!: (value: { items: Cohort[]; next_cursor: null }) => void;
  api.listCohorts.mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }));
  const view = render(<CohortsPage />);
  orgId = "org-b";
  api.listCohorts.mockResolvedValue({ items: [{ ...cohort, name: "New organization" }], next_cursor: null });
  view.rerender(<CohortsPage />);
  await screen.findByRole("heading", { name: "New organization" });
  await act(async () => { resolveOld({ items: [{ ...cohort, name: "Private previous class" }], next_cursor: null }); });
  expect(screen.queryByRole("heading", { name: "Private previous class" })).not.toBeInTheDocument();
});

test("account changes reset scoped lists as well as organization changes", async () => {
  const view = render(<CohortsPage />);
  await screen.findByRole("heading", { name: "Alpha class" });
  userId = "different-user";
  api.listCohorts.mockResolvedValue(empty);
  view.rerender(<CohortsPage />);
  expect(screen.queryByRole("heading", { name: "Alpha class" })).not.toBeInTheDocument();
  await screen.findByText(/No classes are available/);
});

test("only root cohorts are offered as parents", async () => {
  api.listCohorts.mockResolvedValue({ items: [cohort, { ...cohort, id: "child", name: "Nested child", parent_cohort_id: "cohort-a" }], next_cursor: null });
  render(<CohortsPage />);
  expect(await screen.findByRole("option", { name: "Alpha class" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "Nested child" })).not.toBeInTheDocument();
});

test("admins create a shallow cohort with the selected root parent", async () => {
  api.createCohort.mockResolvedValue({ ...cohort, id: "new-cohort" });
  render(<CohortsPage />);
  fireEvent.change(screen.getByLabelText("Name"), { target: { value: "New intake" } });
  const root = await screen.findByRole("option", { name: "Alpha class" });
  fireEvent.change(root.closest("select")!, { target: { value: "cohort-a" } });
  fireEvent.click(screen.getByRole("button", { name: "Create class" }));
  await waitFor(() => expect(api.createCohort).toHaveBeenCalledWith({ name: "New intake", kind: "class", parent_cohort_id: "cohort-a" }, "org-a"));
});

test("archived cohorts remain discoverable without mixing them into active selectors", async () => {
  render(<CohortsPage />);
  await screen.findByRole("heading", { name: "Alpha class" });
  api.listCohorts.mockResolvedValue({ items: [{ ...cohort, name: "Archived intake", status: "archived" }], next_cursor: null });
  fireEvent.change(screen.getByLabelText("Show classes"), { target: { value: "archived" } });
  await screen.findByRole("heading", { name: "Archived intake" });
  expect(api.listCohorts).toHaveBeenCalledWith(undefined, "archived");
});

test("roster administration saves independent facilitator delegation flags", async () => {
  api.setMember.mockResolvedValue({ user_id: "user-b", name: "Learner B", role: "facilitator", can_assign: true, can_report: false });
  render(<CohortDetailPage cohortId="cohort-a" />);
  fireEvent.click(await screen.findByLabelText("Learner B"));
  fireEvent.change(screen.getByLabelText("Membership role"), { target: { value: "facilitator" } });
  fireEvent.click(screen.getByLabelText("Can view progress and attempts"));
  fireEvent.click(screen.getByRole("button", { name: "Save membership" }));
  await waitFor(() => expect(api.setMember).toHaveBeenCalledWith("cohort-a", { user_id: "user-b", role: "facilitator", can_assign: true, can_report: false }, "org-a"));
  expect(api.memberOptions).toHaveBeenCalledWith(undefined);
  expect(api.recipientOptions).not.toHaveBeenCalled();
});

test("cohort progress uses server-authorized completion, average and outstanding counts", async () => {
  role = "facilitator";
  api.getCohort.mockResolvedValue({ ...cohort, can_manage: false });
  render(<CohortDetailPage cohortId="cohort-a" />);
  expect(await screen.findByText("50%")).toBeInTheDocument();
  expect(screen.getByText("75%")).toBeInTheDocument();
  expect(screen.getByText("1/2")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Save membership" })).not.toBeInTheDocument();
  expect(api.progress).toHaveBeenCalledWith("cohort-a", undefined);
});

test("assignment delegation does not imply reporting permission", async () => {
  role = "facilitator";
  api.getCohort.mockResolvedValue({ ...cohort, can_manage: false, can_assign: true, can_report: false });
  render(<CohortDetailPage cohortId="cohort-a" />);
  await screen.findByText("Alpha class");
  expect(api.progress).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: "Assign quiz" })).toBeInTheDocument();
});

test("delegated cohort creation is accessible even when the organization role is learner", async () => {
  role = "learner";
  router.query = { cohort: "cohort-a" };
  render(<AssignmentsPage />);
  expect(await screen.findByLabelText("Assignment title")).toBeInTheDocument();
  expect(await screen.findByRole("option", { name: "Alpha class" })).toBeInTheDocument();
  expect(screen.queryByLabelText("Named recipients")).not.toBeInTheDocument();
  expect(api.recipientOptions).not.toHaveBeenCalled();
  expect(api.memberOptions).not.toHaveBeenCalled();
});

test("report capability can be present without management capability", async () => {
  role = "facilitator";
  api.getAssignment.mockResolvedValue({ ...assignment, can_manage: false, can_report: true });
  render(<AssignmentDetailPage assignmentId="assignment-a" />);
  await screen.findByText("Learner B");
  expect(screen.queryByRole("button", { name: "Close assignment" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "View attempts" }));
  await waitFor(() => expect(api.attempts).toHaveBeenCalledWith("assignment-a", "user-b", undefined));
});

test("the attempt deep link checks report capability before requesting results", async () => {
  api.getAssignment.mockResolvedValue({ ...assignment, can_report: false });
  render(<AssignedAttemptPage assignmentId="assignment-a" userId="user-b" sessionId="session-a" />);
  await screen.findByRole("alert");
  expect(api.attempt).not.toHaveBeenCalled();
});

test("a non-reporting manager is never offered recipient attempt drill-down", async () => {
  api.getAssignment.mockResolvedValue({ ...assignment, can_report: false });
  render(<AssignmentDetailPage assignmentId="assignment-a" />);
  await screen.findByText("Safety knowledge");
  expect(screen.queryByText("Learner B")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "View attempts" })).not.toBeInTheDocument();
  expect(api.attempts).not.toHaveBeenCalled();
});

test("the authorized register loads additional recipients with the server cursor", async () => {
  api.getAssignment.mockResolvedValueOnce({ ...assignment, next_cursor: "page-2" }).mockResolvedValueOnce({
    ...assignment, recipients: [{ ...assignment.recipients![0], recipient_id: "recipient-c", user_id: "user-c", recipient_name: "Learner C" }], next_cursor: null,
  });
  render(<AssignmentDetailPage assignmentId="assignment-a" />);
  await screen.findByText("Learner B");
  expect(api.getAssignment).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Load more" }));
  await screen.findByText("Learner C");
  expect(screen.getByText("Learner B")).toBeInTheDocument();
  expect(api.getAssignment).toHaveBeenLastCalledWith("assignment-a", "page-2");
});

test("attempt detail renders the backend graded_answers contract", async () => {
  api.attempt.mockResolvedValue({ id: "session-a", status: "submitted", percentage: 100, graded_answers: [{
    question_index: 0, question: "Which action is safe?", selected_answer: "Wear protection", correct_answer: "Wear protection", question_type: "multichoice", is_correct: true,
  }] });
  render(<AssignedAttemptPage assignmentId="assignment-a" userId="user-b" sessionId="session-a" />);
  await screen.findByText("1. Which action is safe?");
  expect(screen.getByText("Submitted answer: Wear protection")).toBeInTheDocument();
  expect(api.attempt).toHaveBeenCalledWith("assignment-a", "user-b", "session-a");
});

test("attempt links use the backend attempt id rather than an invented session_id field", async () => {
  api.attempts.mockResolvedValue({ items: [{ id: "session-a", status: "submitted", percentage: 75 }], next_cursor: null });
  render(<AssignmentDetailPage assignmentId="assignment-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "View attempts" }));
  expect(await screen.findByRole("link", { name: "View attempt" })).toHaveAttribute("href", "/assignments/assignment-a/recipients/user-b/attempts/session-a");
});

test("unavailable cohort evidence is not presented as zero progress", async () => {
  api.progress.mockResolvedValue({ items: [{ id: "assignment-a", title: "Safety knowledge", summary_availability: "unavailable" } as Awaited<ReturnType<typeof cohortDeliveryApi.progress>>["items"][number]], next_cursor: null });
  render(<CohortDetailPage cohortId="cohort-a" />);
  expect(await screen.findByText("Completion evidence unavailable")).toBeInTheDocument();
  expect(screen.queryByText("0%")).not.toBeInTheDocument();
});

async function fillAssignmentForm() {
  fireEvent.click(await screen.findByRole("button", { name: "Assign quiz" }));
  const quiz = await screen.findByRole("option", { name: "Quiz one" });
  fireEvent.change(quiz.closest("select")!, { target: { value: "quiz-a" } });
  const group = await screen.findByRole("option", { name: "Alpha class" });
  fireEvent.change(group.closest("select")!, { target: { value: "cohort-a" } });
  fireEvent.change(screen.getByLabelText("Assignment title"), { target: { value: "Safety knowledge" } });
  fireEvent.change(screen.getByLabelText("Closes at"), { target: { value: "2035-10-30T12:00" } });
}

test("navigation failure after creation preserves a successful result and its link", async () => {
  router.push.mockRejectedValueOnce(new Error("navigation cancelled"));
  render(<AssignmentsPage />);
  await fillAssignmentForm();
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  expect(await screen.findByRole("link", { name: "Open created assignment" })).toHaveAttribute("href", "/assignments/assignment-a");
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Assignment created, but the page could not be opened. Use the link below."));
  expect(toast.success).toHaveBeenCalledWith("Assignment created.");
  expect(api.createAssignment).toHaveBeenCalledTimes(1);
  expect(api.createAssignment.mock.calls[0][2]).toBe("org-a");
});

test("failed unchanged creates reuse their key, edits use a new key, success releases the key", async () => {
  api.createAssignment.mockRejectedValueOnce(new Error("lost response")).mockRejectedValueOnce(new Error("still unavailable"));
  render(<AssignmentsPage />);
  await fillAssignmentForm();
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(2));
  expect(api.createAssignment.mock.calls[0][1]).toBe("key-1");
  expect(api.createAssignment.mock.calls[1][1]).toBe("key-1");
  fireEvent.change(screen.getByLabelText("Assignment title"), { target: { value: "Edited intent" } });
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(router.push).toHaveBeenCalledTimes(1));
  expect(api.createAssignment.mock.calls[2][1]).toBe("key-2");
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(router.push).toHaveBeenCalledTimes(2));
  expect(api.createAssignment.mock.calls[3][1]).toBe("key-3");
});

test("cohort versus direct targets are mutually exclusive in create requests", async () => {
  render(<AssignmentsPage />);
  await fillAssignmentForm();
  fireEvent.click(screen.getByLabelText("Named recipients"));
  fireEvent.click(await screen.findByLabelText("Learner B"));
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(api.createAssignment).toHaveBeenCalled());
  const [input] = api.createAssignment.mock.calls[0];
  expect(input.recipient_user_ids).toEqual(["user-b"]);
  expect(input).not.toHaveProperty("cohort_id");
  expect(api.recipientOptions).toHaveBeenCalledWith(undefined);
  expect(api.memberOptions).not.toHaveBeenCalled();
});

test.each(["owner", "admin", "facilitator"])("%s direct recipient selection uses only the assignment picker and paginates", async (organizationRole) => {
  role = organizationRole;
  api.recipientOptions.mockResolvedValueOnce({ items: [{ user_id: "user-b", name: "Learner B" }], next_cursor: "recipients-next" })
    .mockResolvedValueOnce({ items: [{ user_id: "user-c", name: "Learner C" }], next_cursor: null });
  render(<AssignmentsPage />);
  await fillAssignmentForm();
  fireEvent.click(screen.getByLabelText("Named recipients"));
  fireEvent.click(await screen.findByLabelText("Learner B"));
  fireEvent.click(screen.getByRole("button", { name: "Load more" }));
  fireEvent.click(await screen.findByLabelText("Learner C"));
  expect(screen.getByLabelText("Learner B")).toBeChecked();
  expect(api.recipientOptions).toHaveBeenNthCalledWith(1, undefined);
  expect(api.recipientOptions).toHaveBeenNthCalledWith(2, "recipients-next");
  expect(api.memberOptions).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(api.createAssignment).toHaveBeenCalled());
  expect(api.createAssignment.mock.calls[0][0].recipient_user_ids).toEqual(["user-b", "user-c"]);
});

test.each(["learner", "guardian", "author", "auditor"])("a delegated cohort facilitator with org role %s is not offered direct mode", async (organizationRole) => {
  role = organizationRole;
  router.query = { cohort: "cohort-a" };
  render(<AssignmentsPage />);
  await screen.findByLabelText("Assignment title");
  expect(screen.queryByLabelText("Named recipients")).not.toBeInTheDocument();
  expect(api.recipientOptions).not.toHaveBeenCalled();
  expect(api.memberOptions).not.toHaveBeenCalled();
});

test("a changed organization role removes direct mode and cannot submit its stale recipient selection", async () => {
  const view = render(<AssignmentsPage />);
  await fillAssignmentForm();
  fireEvent.click(screen.getByLabelText("Named recipients"));
  fireEvent.click(await screen.findByLabelText("Learner B"));
  role = "learner";
  view.rerender(<AssignmentsPage />);
  expect(screen.queryByLabelText("Named recipients")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Learner B")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Create assignment" }));
  await waitFor(() => expect(api.createAssignment).toHaveBeenCalled());
  expect(api.createAssignment.mock.calls[0][0]).toMatchObject({ cohort_id: "cohort-a" });
  expect(api.createAssignment.mock.calls[0][0]).not.toHaveProperty("recipient_user_ids");
});

test("starting uses the existing live-session token and redirect contract", async () => {
  api.startAssignment.mockResolvedValue({ session_id: "session-a", participant_token: "participant-token", redirect_url: "/live/session-a" } as Awaited<ReturnType<typeof cohortDeliveryApi.startAssignment>>);
  render(<MyAssignmentsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Start assignment" }));
  await waitFor(() => expect(saveParticipantToken).toHaveBeenCalledWith("session-a", "participant-token"));
  expect(router.push).toHaveBeenCalledWith("/live/session-a");
});

test("in-progress assignments resume through authenticated start without a client-side new attempt", async () => {
  api.myAssignments.mockResolvedValue({ items: [{ ...assignment, recipient_status: "in_progress", attempts_used: 1, can_start: false, can_resume: true }], next_cursor: null });
  api.startAssignment.mockResolvedValue({ session_id: "existing-session", participant_token: "rotated-token", redirect_url: "/live-quiz/existing-session" } as Awaited<ReturnType<typeof cohortDeliveryApi.startAssignment>>);
  render(<MyAssignmentsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Resume assignment" }));
  await waitFor(() => expect(api.startAssignment).toHaveBeenCalledTimes(1));
  expect(api.startAssignment).toHaveBeenCalledWith("assignment-a", "org-a");
  expect(saveParticipantToken).toHaveBeenCalledWith("existing-session", "rotated-token");
  expect(router.push).toHaveBeenCalledWith("/live-quiz/existing-session");
  expect(screen.queryByRole("button", { name: "Retry assignment" })).not.toBeInTheDocument();
});

test("late start responses after an organization switch never navigate or save tokens", async () => {
  let finish!: (value: Awaited<ReturnType<typeof cohortDeliveryApi.startAssignment>>) => void;
  api.startAssignment.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  const view = render(<MyAssignmentsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Start assignment" }));
  orgId = "org-b";
  view.rerender(<MyAssignmentsPage />);
  await act(async () => { finish({ session_id: "old-session", participant_token: "old-token", redirect_url: "/old" } as Awaited<ReturnType<typeof cohortDeliveryApi.startAssignment>>); });
  expect(saveParticipantToken).not.toHaveBeenCalled();
  expect(router.push).not.toHaveBeenCalled();
});

test("a failed start reports the server error", async () => {
  api.startAssignment.mockRejectedValue({ response: { data: { detail: "No attempts remain" } } });
  render(<MyAssignmentsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Start assignment" }));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("No attempts remain"));
});

test("closing requires explicit confirmation and cancellation sends no mutation", async () => {
  api.closeAssignment.mockResolvedValue({ ...assignment, status: "closed" });
  render(<AssignmentDetailPage assignmentId="assignment-a" />);
  fireEvent.click(await screen.findByRole("button", { name: "Close assignment" }));
  expect(api.closeAssignment).not.toHaveBeenCalled();
  expect(screen.getByRole("dialog")).toHaveTextContent("cannot be reopened");
  fireEvent.click(screen.getByRole("button", { name: "Keep open" }));
  expect(api.closeAssignment).not.toHaveBeenCalled();
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Close assignment" }));
  fireEvent.click(await screen.findByRole("button", { name: "Close permanently" }));
  await waitFor(() => expect(api.closeAssignment).toHaveBeenCalledWith("assignment-a", "org-a"));
});
