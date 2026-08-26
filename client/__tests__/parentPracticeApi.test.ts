import { createParentPractice } from "@features/parent-practice/api/parentPracticeApi";
import { api } from "@shared/api/http";

jest.mock("@shared/api/http", () => ({
  api: { post: jest.fn() },
}));

const post = api.post as jest.Mock;
const params = {
  profession: "Multiplication tables — ages 7 to 9",
  audience_type: "children ages 7–9",
  difficulty_level: "easy" as const,
  question_type: "multichoice" as const,
  num_questions: 10,
  custom_instruction: "Use exact multiplication facts.",
};

describe("parentPracticeApi", () => {
  beforeEach(() => {
    post.mockReset();
    delete process.env.NEXT_PUBLIC_PARENT_PRACTICE_ALLOW_FALLBACK;
  });

  test("uses the existing generation endpoint with public live participation", async () => {
    process.env.NEXT_PUBLIC_PARENT_PRACTICE_ALLOW_FALLBACK = "true";
    post.mockResolvedValue({
      data: {
        quiz_id: "quiz-1",
        access_code: "ABC123",
        questions: Array.from({ length: 10 }, (_, index) => ({
          question: `Question ${index + 1}`,
        })),
      },
    });

    await createParentPractice(params, 27);

    expect(post).toHaveBeenCalledWith(
      "/api/get-questions",
      expect.objectContaining({
        ...params,
        live_quiz_enabled: true,
        participant_access_mode: "public",
        invited_emails: [],
        send_email_invitations: false,
        allow_fallback: true,
        time_limit_minutes: 27,
      }),
    );
  });

  test.each([0, -1, 181, 2.5, Number.NaN])(
    "rejects invalid duration %s before making a request",
    async (duration) => {
      await expect(createParentPractice(params, duration)).rejects.toThrow(
        /between 1 and 180 minutes/i,
      );
      expect(post).not.toHaveBeenCalled();
    },
  );

  test("rejects unrelated generic fallback content", async () => {
    post.mockResolvedValue({
      data: {
        ai_down: true,
        quiz_id: "quiz-1",
        access_code: "ABC123",
        questions: [{ question: "Unrelated mock question" }],
      },
    });

    await expect(createParentPractice(params)).rejects.toThrow(
      /temporarily unavailable/i,
    );
  });
});
