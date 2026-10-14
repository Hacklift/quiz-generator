"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";
import {
  trainingRunApi,
  type TrainingAssignment,
} from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, CONTAINER, Kicker } from "@shared/ui/quizwerk";

const stateLabel = (assignment: TrainingAssignment) => {
  if (assignment.status === "completed")
    return `Completed${assignment.latest_percentage != null ? ` · ${assignment.latest_percentage}%` : ""}`;
  if (!assignment.can_retry && assignment.status === "in_progress")
    return "Attempt in progress";
  if (
    !assignment.can_retry &&
    new Date(assignment.latest_start_at) < new Date()
  )
    return "Start window closed";
  if (
    !assignment.can_retry &&
    assignment.max_attempts != null &&
    assignment.attempts_used >= assignment.max_attempts
  )
    return "Attempts used";
  if (assignment.is_overdue) return "Overdue";
  return assignment.due_at
    ? `Due ${new Date(assignment.due_at).toLocaleString()}`
    : "No due date";
};

export default function AssignedTrainingPage() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const [assignments, setAssignments] = useState<TrainingAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [startingId, setStartingId] = useState<string | null>(null);

  const load = async () => {
    try {
      setIsLoading(true);
      setAssignments(await trainingRunApi.listMyAssignments());
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not load assigned training.",
      );
    } finally {
      setIsLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);

  const start = async (assignmentId: string) => {
    try {
      setStartingId(assignmentId);
      const session = await trainingRunApi.startAssignment(assignmentId);
      saveParticipantToken(session.session_id, session.participant_token);
      await router.push(session.redirect_url);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not start training.");
    } finally {
      setStartingId(null);
    }
  };

  return (
    <RequireAuth
      title={uiText("m6bc7e9d5dd0c3d67")}
      description={uiText("m6f06d75450152a0f")}
    >
      <div className="flex min-h-screen flex-col bg-paper text-ink">
        <NavBar />
        <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
          <header className="border-b-2 border-divider pb-[28px]">
            <Kicker>{uiText("m7dc9f1f17e61d3c7")}</Kicker>
            <div className="flex flex-wrap items-end justify-between gap-[16px]">
              <div>
                <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
                  {uiText("mdbf11bd849e21820")}
                </h1>
                <p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
                  {uiText("m91a5ec2e767ccb8c")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void load()}
                className={BTN_GHOST}
              >
                {uiText("m0e91610117029a62")}
              </button>
            </div>
          </header>
          {isLoading ? (
            <div className="flex min-h-[40vh] items-center justify-center">
              <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-brand" />
            </div>
          ) : (
            <section
              className="pt-[36px]"
              aria-label={uiText("m25f73226d2bb8ddf")}
            >
              <div className="grid gap-[12px]">
                {assignments.length ? (
                  assignments.map((assignment) => (
                    <article
                      key={assignment.id}
                      className="flex flex-wrap items-center justify-between gap-[20px] border-2 border-divider bg-paper p-[20px]"
                    >
                      <div>
                        <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
                          {assignment.kind === "compliance"
                            ? uiText("m4a109cc49467be33")
                            : uiText("m36a798e3f39239cc")}
                        </p>
                        <h2 className="mt-[8px] text-[18px] font-extrabold">
                          {assignment.title}
                        </h2>
                        <p className="mt-[5px] text-[14px] text-ink/70">
                          {stateLabel(assignment)} · {assignment.attempts_used}/
                          {assignment.max_attempts ?? "∞"}{" "}
                          {uiText("mbc99fa508af3e8ba")}
                        </p>
                      </div>
                      {assignment.can_retry ? (
                        <button
                          type="button"
                          disabled={startingId === assignment.id}
                          onClick={() => void start(assignment.id)}
                          className={`${BTN_PRIMARY} disabled:opacity-50`}
                        >
                          {startingId === assignment.id
                            ? uiText("m82b93630a921dddf")
                            : assignment.attempts_used
                              ? uiText("mdd15582433df54b6")
                              : uiText("m39d9d2a95571eafb")}
                        </button>
                      ) : (
                        <span className="text-[14px] font-extrabold text-ink/60">
                          {assignment.status === "completed"
                            ? uiText("m22a970d2e5b1cc23")
                            : uiText("mca184496974204a0")}
                        </span>
                      )}
                    </article>
                  ))
                ) : (
                  <p className="border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
                    {uiText("m0627a9e3ea4ec72b")}
                  </p>
                )}
              </div>
            </section>
          )}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
