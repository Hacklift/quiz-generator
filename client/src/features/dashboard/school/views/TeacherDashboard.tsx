"use client";

import React from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import { personaGenerateHref } from "@shared/config/persona";
import { titleCaseTerm } from "@shared/config/terminology";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

interface TeacherPreset {
  id: string;
  title: string;
  badge: string;
  description: string;
  href: string;
}

function teacherPresetHref(
  persona: DashboardViewProps["persona"],
  preset: string,
) {
  return `${personaGenerateHref(persona.userType)}&preset=${preset}`;
}

export default function TeacherDashboard({ persona }: DashboardViewProps) {
  const router = useRouter();
  const t = useTerms();

  const presets: TeacherPreset[] = [
    {
      id: "class-quiz",
      title: "Class quiz",
      badge: "In-class / Auto-marked",
      description: `Run a live, interactive check during your ${t(
        "session",
      )}. Generates multiple-choice and short answers pre-set for ${t(
        "learner",
        "plural",
      )}.`,
      href: teacherPresetHref(persona, "class-quiz"),
    },
    {
      id: "homework-check",
      title: "Homework check",
      badge: "Take-home / Answer key",
      description: `Create ${t(
        "assignment",
      )} with detailed answer explanations suited for independent submission and rapid marking.`,
      href: teacherPresetHref(persona, "homework-check"),
    },
    {
      id: "exam-revision",
      title: "Exam revision",
      badge: "Revision / Mixed formats",
      description:
        "Comprehensive practice set covering key topics and core curriculum concepts before upcoming exams.",
      href: teacherPresetHref(persona, "exam-revision"),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="teacher-presets-heading"
      >
        <Kicker>Teacher dashboard</Kicker>
        <h2
          id="teacher-presets-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          Classroom assessment presets
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          Jumpstart your assessment without generic configuration. Every preset
          is pre-configured for {t("learner", "plural")} with marking-ready
          formats.
        </p>

        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[20px]">
          {presets.map((preset) => (
            <article
              key={preset.id}
              className="flex flex-col justify-between border-2 border-divider bg-paper p-[20px] text-left transition hover:border-ink/60 hover:bg-ink/[0.02]"
            >
              <div>
                <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
                  {preset.badge}
                </p>
                <h3 className="mt-[10px] text-[17px] font-extrabold text-ink">
                  {preset.title}
                </h3>
                <p className="mt-[8px] text-[13.5px] leading-[22px] text-ink/70">
                  {preset.description}
                </p>
              </div>

              <button
                type="button"
                onClick={() => router.push(preset.href)}
                className={`${BTN_PRIMARY} mt-[20px] w-full`}
                aria-label={`Create ${preset.title}`}
              >
                Create {preset.title}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="teacher-results-heading"
      >
        <Kicker>{titleCaseTerm(t("group"))} assessment</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="teacher-results-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {titleCaseTerm(t("group"))} session results and marking
            </h2>
            <p className="mt-[6px] max-w-[56ch] text-[14.5px] leading-[24px] text-ink/70">
              Inspect participant scores, per-question breakdown, and mark
              submissions from your live {t("session", "plural")}.
            </p>
          </div>

          <div className="flex flex-wrap gap-[12px]">
            <button
              type="button"
              onClick={() => router.push("/my-live-quizzes")}
              className={BTN_PRIMARY}
              aria-label={`View live ${t("session")} results`}
            >
              View live {t("session")} results
            </button>
            <button
              type="button"
              onClick={() => router.push("/quiz_history")}
              className={BTN_GHOST}
              aria-label={`View ${t("assignment")} history`}
            >
              All {t("assignment", "plural")}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
