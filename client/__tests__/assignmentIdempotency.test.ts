import { assignmentCreationKey, assignmentFingerprint, completeAssignmentCreation } from "@features/cohorts/lib/assignmentIdempotency";
import type { AssignmentInput } from "@features/cohorts/api/cohortDeliveryApi";

const input: AssignmentInput = {
  quiz_id: "quiz", recipient_user_ids: ["b", "a"], title: "Safety", closes_at: "2035-01-01T12:00:00Z",
  max_attempts: 2, time_limit_minutes: 20, passing_threshold_percentage: 80, send_email_invitations: false,
};
test("recipient ordering and duplicates do not change assignment intent", () => {
  expect(assignmentFingerprint(input)).toBe(assignmentFingerprint({ ...input, recipient_user_ids: ["a", "b", "a"] }));
});
test("every assignment setting participates in the retry fingerprint", () => {
  expect(assignmentFingerprint(input)).not.toBe(assignmentFingerprint({ ...input, passing_threshold_percentage: 90 }));
  expect(assignmentFingerprint(input)).not.toBe(assignmentFingerprint({ ...input, available_from: "2034-01-01T12:00:00Z" }));
});
test("success clears only the completed payload, preserving other uncertain requests", () => {
  Object.defineProperty(crypto, "randomUUID", { configurable: true, value: jest.fn().mockReturnValueOnce("first").mockReturnValueOnce("edited").mockReturnValueOnce("fresh") });
  const keys = new Map<string, string>();
  const edited = { ...input, title: "Edited" };
  expect(assignmentCreationKey(keys, input)).toBe("first");
  expect(assignmentCreationKey(keys, edited)).toBe("edited");
  completeAssignmentCreation(keys, input);
  expect(assignmentCreationKey(keys, edited)).toBe("edited");
  expect(assignmentCreationKey(keys, input)).toBe("fresh");
});
