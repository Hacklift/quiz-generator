"use client";
import { useTranslation } from "react-i18next";

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
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const t = useTerms();

  const presets: LecturerPreset[] = [
    {
      id: "lecture-recap",
      title: uiText("m9f164b0f032b786d"),
      badge: "Post-lecture / Retention check",
      description: uiText("m56c74aad54c9863d", {
        value0: t("group"),
        value1: t("assignment"),
        value2: t("session"),
      }),
      href: lecturerPresetHref(persona, "lecture-recap"),
    },
    {
      id: "seminar-prep",
      title: uiText("me318131ee57f1056"),
      badge: "Pre-seminar / Readiness check",
      description: uiText("m440711e4b9d3e8ca", {
        value0: t("group"),
        value1: t("assignment"),
      }),
      href: lecturerPresetHref(persona, "seminar-prep"),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="lecturer-live-heading"
      >
        <Kicker>{uiText("m94f506b7d34d68a2")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="lecturer-live-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("m05c850f4bdf692cc")}
              {t("session")} {uiText("m75b99b5e3a11e30b")}
              {t("group")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("mf3212c4d5d0cfd2f")}
              {t("group", "plural")} {uiText("m0c1d84c48ce4804e")}
              {t("group")} {uiText("m6c55798ab10d843d")}
              {t("learner", "plural")} {uiText("m4a7b489bf3310639")}
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push("/my-live-quizzes")}
            className={`${BTN_PRIMARY} px-[28px] py-[14px] text-[16px]`}
            aria-label={uiText("m3e76d87073ed499f", { value0: t("session") })}
          >
            {uiText("md2cfdf716a507690")}
            {t("session")}
          </button>
        </div>

        <div className="mt-[20px] border-2 border-divider bg-paper p-[20px]">
          <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
            {uiText("m690dbe9dc0993c42")}
            {t("session", "plural")}
          </p>
          <p className="mt-[8px] text-[13.5px] leading-[22px] text-ink/70">
            {uiText("m947363a28565f3fc")}
            {t("session")}
            {uiText("m85dea3df1f9cfcb1")}
            {t("group")} {uiText("m426a630ace303b2c")}
          </p>
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="lecturer-presets-heading"
      >
        <Kicker>{uiText("ma2c8e03408a0b012")}</Kicker>
        <h2
          id="lecturer-presets-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          {uiText("mfd5383c2f9a05cd0")}
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          {uiText("m7f1cf035027ae984")}
          {t("assignment")} {uiText("me43ee3eb508e991f")}
          {t("group", "plural")}.
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
                {uiText("m4759498ac2a719c6")}
                {preset.title}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="lecturer-results-heading"
      >
        <Kicker>
          {titleCaseTerm(t("group"))} {uiText("mc099142bc3186ded")}
        </Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="lecturer-results-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {titleCaseTerm(t("group"))} {t("session")}{" "}
              {uiText("mc099142bc3186ded")}
            </h2>
            <p className="mt-[6px] max-w-[56ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("mb4acaa153ba09ba6")} {t("session", "plural")}
              {uiText("mfdda72301790e2d0")}
            </p>
          </div>

          <div className="flex flex-wrap gap-[12px]">
            <button
              type="button"
              onClick={() => router.push("/my-live-quizzes")}
              className={BTN_PRIMARY}
              aria-label={uiText("mc6728d026c2fc4b5", { value0: t("session") })}
            >
              {uiText("mfbe9628a9380f412")}
              {t("session")} {uiText("mc099142bc3186ded")}
            </button>
            <button
              type="button"
              onClick={() => router.push("/quiz_history")}
              className={BTN_GHOST}
              aria-label={uiText("mde8eafec5e6fe027", {
                value0: t("assignment", "plural"),
              })}
            >
              {uiText("ma52ace420f2175d0")}
              {t("assignment", "plural")}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
