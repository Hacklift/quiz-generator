import { api } from "@shared/api/http";
import { cohortDeliveryApi } from "@features/cohorts/api/cohortDeliveryApi";

jest.mock("@shared/api/http", () => ({ api: { get: jest.fn(), post: jest.fn(), patch: jest.fn(), delete: jest.fn() } }));

beforeEach(() => { jest.resetAllMocks(); });

test("assignment recipient options use the dedicated endpoint and preserve pagination", async () => {
  const page = { items: [{ user_id: "user-a", name: "Learner A" }], next_cursor: "next-page" };
  jest.mocked(api.get).mockResolvedValue({ data: page });
  expect(await cohortDeliveryApi.recipientOptions("previous-page")).toBe(page);
  expect(api.get).toHaveBeenCalledWith("/api/v1/assignments/recipient-options", { params: { cursor: "previous-page" } });
});

test("roster member options retain the admin-only cohort endpoint", async () => {
  const page = { items: [], next_cursor: null };
  jest.mocked(api.get).mockResolvedValue({ data: page });
  expect(await cohortDeliveryApi.memberOptions()).toBe(page);
  expect(api.get).toHaveBeenCalledWith("/api/cohorts/member-options", { params: undefined });
});

test("write requests carry their original workspace intent without selecting a tenant", async () => {
  jest.mocked(api.post).mockResolvedValue({ data: {} });
  jest.mocked(api.patch).mockResolvedValue({ data: {} });
  jest.mocked(api.delete).mockResolvedValue({ data: {} });
  const input = { name: "Class A", kind: "class" as const, parent_cohort_id: null };
  const member = { user_id: "recipient", role: "member" as const, can_assign: false, can_report: false };
  const assignment = { quiz_id: "quiz-a", cohort_id: "cohort-a", title: "Test",
    closes_at: "2035-10-30T12:00:00Z", max_attempts: 1 as const,
    time_limit_minutes: 20, passing_threshold_percentage: 80, send_email_invitations: false };
  await cohortDeliveryApi.createCohort(input, "original-org");
  await cohortDeliveryApi.updateCohort("cohort-a", input, "original-org");
  await cohortDeliveryApi.archiveCohort("cohort-a", "original-org");
  await cohortDeliveryApi.setMember("cohort-a", member, "original-org");
  await cohortDeliveryApi.removeMember("cohort-a", "recipient", "original-org");
  await cohortDeliveryApi.createAssignment(assignment, "intent-key", "original-org");
  await cohortDeliveryApi.startAssignment("assignment-a", "original-org");
  await cohortDeliveryApi.closeAssignment("assignment-a", "original-org");
  const config = { headers: { "X-Organization-ID": "original-org" } };
  expect(api.post).toHaveBeenCalledWith("/api/cohorts", input, config);
  expect(api.patch).toHaveBeenCalledWith("/api/cohorts/cohort-a", input, config);
  expect(api.delete).toHaveBeenCalledWith("/api/cohorts/cohort-a", config);
  expect(api.post).toHaveBeenCalledWith("/api/cohorts/cohort-a/members", member, config);
  expect(api.delete).toHaveBeenCalledWith("/api/cohorts/cohort-a/members/recipient", config);
  expect(api.post).toHaveBeenCalledWith("/api/v1/assignments", assignment,
    { headers: { "X-Organization-ID": "original-org", "Idempotency-Key": "intent-key" } });
  expect(api.post).toHaveBeenCalledWith("/api/v1/assignments/assignment-a/start", undefined, config);
  expect(api.post).toHaveBeenCalledWith("/api/v1/assignments/assignment-a/close", { confirm: true }, config);
});
