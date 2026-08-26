"use client";

import React from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import { personaGenerateHref } from "@shared/config/persona";
import { titleCaseTerm } from "@shared/config/terminology";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

interface LecturerPreset {
  id: string;
  title: string;
  badge: string;
  description: string;
  href: string;
}

function lecturerPresetHref(
  persona: DashboardViewProps["persona"],
  preset: string,
) {
  return `${personaGenerateHref(persona.userType)}&preset=${preset}`;
}

export default function LecturerDashboard({ persona }: DashboardViewProps) {
  const router = useRouter();
  const t = useTerms();

  const presets: LecturerPreset[] = [
    {
      id: "lecture-recap",
      title: "Lecture recap",
      badge: "Post-lecture / Retention check",
      description: `Reinforce what your ${t(
        "group",
      )} just covered with a short recap ${t(
        "assignment",
      )} they can complete right after the ${t("session")}.`,
      href: lecturerPresetHref(persona, "lecture-recap"),
    },
    {
      id: "seminar-prep",
      title: "Seminar prep",
      badge: "Pre-seminar / Readiness check",
      description: `Check your ${t(
        "group",
      )} has done the reading before seminar with a quick, low-stakes ${t(
        "assignment",
      )}.`,
      href: lecturerPresetHref(persona, "seminar-prep"),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="lecturer-live-heading"
      >
        <Kicker>Live session</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="lecturer-live-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              Run a live {t("session")} for your {t("group")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              Built for large {t("group", "plural")} — put a join code on the
              projector, track {t("group")} size as {t("learner", "plural")}
              {" "}join, and score them in real time.
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push("/my-live-quizzes")}
            className={`${BTN_PRIMARY} px-[28px] py-[14px] text-[16px]`}
            aria-label={`Start live ${t("session")}`}
          >
            Start live {t("session")}
          </button>
        </div>

        <div className="mt-[20px] border-2 border-divider bg-paper p-[20px]">
          <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
            Recent {t("session", "plural")}
          </p>
          <p className="mt-[8px] text-[13.5px] leading-[22px] text-ink/70">
            Nothing here yet. Once you start a live {t("session")}, it will
            show up here with {t("group")} size and participation counts.
          </p>
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="lecturer-presets-heading"
      >
        <Kicker>Lecturer dashboard</Kicker>
        <h2
          id="lecturer-presets-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          Quick-create presets
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          Jumpstart your {t("assignment")} without generic configuration.
          Every preset is pre-configured for large {t("group", "plural")}.
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
        aria-labelledby="lecturer-results-heading"
      >
        <Kicker>{titleCaseTerm(t("group"))} results</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="lecturer-results-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {titleCaseTerm(t("group"))} {t("session")} results
            </h2>
            <p className="mt-[6px] max-w-[56ch] text-[14.5px] leading-[24px] text-ink/70">
              Inspect participation and scores from your live{" "}
              {t("session", "plural")}, optimised for viewing on a projector.
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
              aria-label={`All ${t("assignment", "plural")} history`}
            >
              All {t("assignment", "plural")}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
