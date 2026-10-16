"use client";
import { useTranslation } from "react-i18next";

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
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const t = useTerms();

  const presets: TeacherPreset[] = [
    {
      id: "class-quiz",
      title: uiText("md7de3c47d3ed1f06"),
      badge: "In-class / Auto-marked",
      description: uiText("m72fca694bfb26042", {
        value0: t("session"),
        value1: t("learner", "plural"),
      }),
      href: teacherPresetHref(persona, "class-quiz"),
    },
    {
      id: "homework-check",
      title: uiText("mcd8487e72acad79f"),
      badge: "Take-home / Answer key",
      description: uiText("m2d1e38422f214ad7", { value0: t("assignment") }),
      href: teacherPresetHref(persona, "homework-check"),
    },
    {
      id: "exam-revision",
      title: uiText("m53c1afad724e63a9"),
      badge: "Revision / Mixed formats",
      description: uiText("mf4b4ed76766c4d7a"),
      href: teacherPresetHref(persona, "exam-revision"),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="teacher-presets-heading"
      >
        <Kicker>{uiText("me7d8da86fdb02358")}</Kicker>
        <h2
          id="teacher-presets-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          {uiText("mc79ebb88be61c53c")}
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          {uiText("m602e2db461b0cb47", { value0: t("learner", "plural") })}
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
                aria-label={uiText("m37a7e45e1b49df1f", {
                  value0: preset.title,
                })}
              >
                {uiText("m37a7e45e1b49df1f", { value0: preset.title })}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="teacher-results-heading"
      >
        <Kicker>
          {uiText("m14ab1f4d77826881", { value0: titleCaseTerm(t("group")) })}
        </Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="teacher-results-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("mcb1d989e57c3ec8b", {
                value0: titleCaseTerm(t("group")),
              })}
            </h2>
            <p className="mt-[6px] max-w-[56ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("md2fec2e9ea36748b", { value0: t("session", "plural") })}
            </p>
          </div>

          <div className="flex flex-wrap gap-[12px]">
            <button
              type="button"
              onClick={() => router.push("/my-live-quizzes")}
              className={BTN_PRIMARY}
              aria-label={uiText("mc6728d026c2fc4b5", { value0: t("session") })}
            >
              {uiText("mc6728d026c2fc4b5", { value0: t("session") })}
            </button>
            <button
              type="button"
              onClick={() => router.push("/quiz_history")}
              className={BTN_GHOST}
              aria-label={uiText("m79830cfc06f30299", {
                value0: t("assignment"),
              })}
            >
              {uiText("mb2899a619eb1f4bb", {
                value0: t("assignment", "plural"),
              })}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
