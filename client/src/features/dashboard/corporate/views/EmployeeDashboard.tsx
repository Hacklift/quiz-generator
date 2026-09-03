"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import { useTerms } from "@features/persona/hooks/useTerms";
import { trainingRunApi, type TrainingAssignment } from "@features/training/api/trainingRunApi";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { personaGenerateHref } from "@shared/config/persona";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

const dueLabel = (assignment: TrainingAssignment) => {
  if (assignment.status === "completed") return "Completed";
  if (assignment.is_overdue) return "Overdue";
  return assignment.due_at
    ? `Due ${new Date(assignment.due_at).toLocaleDateString()}`
    : "No due date";
};

export default function EmployeeDashboard({ persona }: DashboardViewProps) {
  const router = useRouter();
  const t = useTerms();
  const [assignments, setAssignments] = useState<TrainingAssignment[]>([]);
  const [startingId, setStartingId] = useState<string | null>(null);

  useEffect(() => {
    void trainingRunApi
      .listMyAssignments()
      .then(setAssignments)
      .catch(() => setAssignments([]));
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
    <div className="flex flex-col gap-[36px]">
      <section className="border-t-2 border-divider pt-[28px]" aria-labelledby="employee-assigned-heading">
        <Kicker>Your training</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2 id="employee-assigned-heading" className="text-[20px] font-extrabold tracking-[-0.015em] text-ink">Assigned to you</h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              Complete required training at your own pace. Your completed score is visible to the person who assigned it.
            </p>
          </div>
          <button type="button" onClick={() => router.push("/assigned-training")} className={BTN_GHOST}>View all training</button>
        </div>
        {assignments.length ? (
          <div className="mt-[20px] grid gap-[12px]">
            {assignments.slice(0, 4).map((assignment) => (
              <article key={assignment.id} className="flex flex-wrap items-center justify-between gap-[16px] border-2 border-divider bg-paper p-[16px]">
                <div>
                  <h3 className="font-extrabold text-ink">{assignment.title}</h3>
                  <p className="mt-[3px] text-[13px] text-ink/70">
                    {dueLabel(assignment)}{assignment.latest_percentage != null ? ` · ${assignment.latest_percentage}%` : ""}
                  </p>
                </div>
                {assignment.can_retry ? (
                  <button type="button" onClick={() => void start(assignment.id)} disabled={startingId === assignment.id} className={BTN_PRIMARY}>
                    {startingId === assignment.id ? "Starting..." : assignment.attempts_used ? "Retry" : "Start training"}
                  </button>
                ) : <span className="text-[13px] font-extrabold text-ink/60">{assignment.status === "completed" ? "Completed" : "Unavailable"}</span>}
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
            Nothing assigned yet. When a manager assigns training to this verified email, it will appear here.
          </p>
        )}
      </section>

      <section className="border-t-2 border-divider pt-[28px]" aria-labelledby="employee-practice-heading">
        <Kicker>Self-paced practice</Kicker>
        <h2 id="employee-practice-heading" className="text-[20px] font-extrabold tracking-[-0.015em] text-ink">Build your next skill</h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">Generate a private practice {t("quiz")} for any topic you want to improve.</p>
        <button type="button" onClick={() => router.push(personaGenerateHref(persona.userType))} className={`${BTN_PRIMARY} mt-[20px]`}>Create a practice {t("quiz")}</button>
      </section>
    </div>
  );
}
