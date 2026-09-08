"use client";

import React from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import { personaGenerateHref } from "@shared/config/persona";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

interface StudentPreset {
  id: string;
  title: string;
  badge: string;
  description: string;
  href: string;
}

function studentPresetHref(
  persona: DashboardViewProps["persona"],
  preset: string,
) {
  return `${personaGenerateHref(persona.userType)}&preset=${preset}`;
}

export default function StudentDashboard({ persona }: DashboardViewProps) {
  const router = useRouter();
  const t = useTerms();

  const presets: StudentPreset[] = [
    {
      id: "self-test",
      title: "Self-test",
      badge: "Auto-marked / Immediate feedback",
      description: `Practise any topic with an auto-marked ${t("assignment")} that scores itself the moment you finish, so you know straight away what to revise next.`,
      href: studentPresetHref(persona, "self-test"),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="student-practice-heading"
      >
        <Kicker>Practice</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="student-practice-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              Practise by subject
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              Pick a topic and get a fresh {t("assignment")} to work through —
              every attempt is saved to your {t("report")} so you can see how
              you are doing over time.
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push(personaGenerateHref(persona.userType))}
            className={`${BTN_PRIMARY} px-[28px] py-[14px] text-[16px]`}
            aria-label="Practise a topic"
          >
            Practise a topic
          </button>
        </div>

        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-[16px]">
          <button
            type="button"
            onClick={() => router.push("/quiz_history")}
            className="flex flex-col items-start gap-[6px] border-2 border-divider bg-paper p-[20px] text-left transition hover:border-ink/60 hover:bg-ink/[0.02]"
            aria-label={`My ${t("report")} history`}
          >
            <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
              History
            </p>
            <p className="text-[15px] font-extrabold text-ink">
              My {t("report")} history
            </p>
            <p className="text-[13.5px] leading-[20px] text-ink/70">
              See every {t("assignment")} you have taken and your score on each
              one.
            </p>
          </button>

          <button
            type="button"
            onClick={() => router.push("/quiz_history")}
            className="flex flex-col items-start gap-[6px] border-2 border-divider bg-paper p-[20px] text-left transition hover:border-ink/60 hover:bg-ink/[0.02]"
            aria-label="Retry weak areas"
          >
            <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
              Retry
            </p>
            <p className="text-[15px] font-extrabold text-ink">
              Retry weak areas
            </p>
            <p className="text-[13.5px] leading-[20px] text-ink/70">
              Jump back into topics where your scores were lowest and try again.
            </p>
          </button>
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="student-presets-heading"
      >
        <Kicker>Student dashboard</Kicker>
        <h2
          id="student-presets-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          Quick-create presets
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          Jumpstart your revision without generic configuration.
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
        aria-labelledby="student-live-heading"
      >
        <Kicker>Live quiz</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="student-live-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              Joining a live {t("session")}?
            </h2>
            <p className="mt-[6px] max-w-[56ch] text-[14.5px] leading-[24px] text-ink/70">
              Got a code? Enter it to join a live {t("session")} and see your
              results as soon as it ends.
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push("/quiz-access")}
            className={BTN_GHOST}
            aria-label="Join a live quiz"
          >
            Join a live quiz
          </button>
        </div>
      </section>
    </div>
  );
}
