"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import { useTerms } from "@features/persona/hooks/useTerms";
import {
  trainingRunApi,
  type TrainingAssignment,
} from "@features/training/api/trainingRunApi";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { personaGenerateHref } from "@shared/config/persona";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import { ROUTES } from "@shared/config/patterns/routes";

const dueLabel = (assignment: TrainingAssignment) => {
  if (assignment.status === "completed") return "Completed";
  if (assignment.is_overdue) return "Overdue";
  return assignment.due_at
    ? `Due ${new Date(assignment.due_at).toLocaleDateString()}`
    : "No due date";
};

export default function EmployeeDashboard({ persona }: DashboardViewProps) {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const t = useTerms();
  const [assignments, setAssignments] = useState<TrainingAssignment[]>([]);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    void trainingRunApi
      .listMyAssignments()
      .then((items) => {
        if (!active) return;
        setAssignments(items);
        setLoadError(false);
      })
      .catch(() => {
        if (active) setLoadError(true);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
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
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="employee-assigned-heading"
      >
        <Kicker>{uiText("m7dc9f1f17e61d3c7")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="employee-assigned-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("mdbf11bd849e21820")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("m38afedb3c7474bc6")}
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.push(ROUTES.ASSIGNED_TRAINING)}
            className={BTN_GHOST}
          >
            {uiText("m1c0a49eb612c5323")}
          </button>
        </div>
        {isLoading ? (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] text-ink/70">
            {uiText("m39f3a5eb5cbeaf53")}
          </p>
        ) : loadError ? (
          <p
            role="alert"
            className="mt-[20px] border-2 border-brand bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70"
          >
            {uiText("m6e71e1e06fce74f6")}
          </p>
        ) : assignments.length ? (
          <div className="mt-[20px] grid gap-[12px]">
            {assignments.slice(0, 4).map((assignment) => (
              <article
                key={assignment.id}
                className="flex flex-wrap items-center justify-between gap-[16px] border-2 border-divider bg-paper p-[16px]"
              >
                <div>
                  <h3 className="font-extrabold text-ink">
                    {assignment.title}
                  </h3>
                  <p className="mt-[3px] text-[13px] text-ink/70">
                    {dueLabel(assignment)}
                    {assignment.latest_percentage != null
                      ? ` · ${assignment.latest_percentage}%`
                      : ""}
                  </p>
                </div>
                {assignment.can_retry ? (
                  <button
                    type="button"
                    onClick={() => void start(assignment.id)}
                    disabled={startingId === assignment.id}
                    className={BTN_PRIMARY}
                  >
                    {startingId === assignment.id
                      ? uiText("m82b93630a921dddf")
                      : assignment.attempts_used
                        ? uiText("m942087cc2d41e013")
                        : uiText("m39d9d2a95571eafb")}
                  </button>
                ) : (
                  <span className="text-[13px] font-extrabold text-ink/60">
                    {assignment.status === "completed"
                      ? uiText("m22a970d2e5b1cc23")
                      : uiText("mca184496974204a0")}
                  </span>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
            {uiText("m25f47bdfcaf976ad")}
          </p>
        )}
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="employee-practice-heading"
      >
        <Kicker>{uiText("m12dbdd92a0079e2e")}</Kicker>
        <h2
          id="employee-practice-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          {uiText("m5f60be183ddf85c4")}
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          {uiText("m340a24d9e7a4773b")}
          {t("quiz")} {uiText("m3d4c1b11ad335907")}
        </p>
        <button
          type="button"
          onClick={() => router.push(personaGenerateHref(persona.userType))}
          className={`${BTN_PRIMARY} mt-[20px]`}
        >
          {uiText("mcdbb6f32fb90f430")}
          {t("quiz")}
        </button>
      </section>
    </div>
  );
}
