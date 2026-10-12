import type { CreateTrainingRunPayload } from "@features/training/api/trainingRunApi";
import {
  clearTrainingRunIdempotencyKey,
  idempotencyKeyForTrainingRun,
  trainingRunIntentFingerprint,
} from "@features/training/lib/trainingRunIdempotency";

const payload = (): CreateTrainingRunPayload => ({
  quiz_id: "quiz-1",
  kind: "business",
  purpose: "onboarding",
  time_limit_minutes: 20,
  closes_at: "2026-09-10T12:00:00.000Z",
  due_at: "2026-09-09T12:00:00.000Z",
  access_mode: "assigned_only",
  recipient_emails: ["learner@example.com"],
  max_attempts: 1,
  send_email_invitations: true,
});

describe("training run idempotency", () => {
  it("reuses a key for the same normalized request intent", () => {
    const keys = new Map<string, string>();
    const createKey = jest.fn(() => "key-1");
    const first = idempotencyKeyForTrainingRun(keys, payload(), createKey);
    const reordered = payload();
    reordered.recipient_emails = [" LEARNER@example.com "];

    const retry = idempotencyKeyForTrainingRun(keys, reordered, createKey);

    expect(first).toBe("key-1");
    expect(retry).toBe("key-1");
    expect(createKey).toHaveBeenCalledTimes(1);
  });

  it("uses a new key after an edited request and preserves the original retry key", () => {
    const keys = new Map<string, string>();
    const createKey = jest
      .fn()
      .mockReturnValueOnce("key-original")
      .mockReturnValueOnce("key-edited");
    const original = payload();
    const edited = payload();
    edited.recipient_emails = ["another@example.com"];

    expect(idempotencyKeyForTrainingRun(keys, original, createKey)).toBe("key-original");
    expect(idempotencyKeyForTrainingRun(keys, edited, createKey)).toBe("key-edited");
    expect(idempotencyKeyForTrainingRun(keys, original, createKey)).toBe("key-original");
    expect(createKey).toHaveBeenCalledTimes(2);
    expect(trainingRunIntentFingerprint(original)).not.toBe(
      trainingRunIntentFingerprint(edited),
    );
  });

  it("releases a successful intent so a later identical run is new", () => {
    const keys = new Map<string, string>();
    const createKey = jest
      .fn()
      .mockReturnValueOnce("key-first-run")
      .mockReturnValueOnce("key-second-run");
    const request = payload();

    expect(idempotencyKeyForTrainingRun(keys, request, createKey)).toBe("key-first-run");
    clearTrainingRunIdempotencyKey(keys, request);
    expect(idempotencyKeyForTrainingRun(keys, request, createKey)).toBe("key-second-run");
  });
});
