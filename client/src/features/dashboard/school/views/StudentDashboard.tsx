"use client";
import { useTranslation } from "react-i18next";

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
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const t = useTerms();

  const presets: StudentPreset[] = [
    {
      id: "self-test",
      title: uiText("m17be10d46feeecbb"),
      badge: "Auto-marked / Immediate feedback",
      description: uiText("m380ec11e82888063", { value0: t("assignment") }),
      href: studentPresetHref(persona, "self-test"),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="student-practice-heading"
      >
        <Kicker>{uiText("md3857b12b4cea2bc")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="student-practice-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("me57c11eda5f86c44")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("mdc742e72c239c50f", {
                value0: t("assignment"),
                value1: t("report"),
              })}
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push(personaGenerateHref(persona.userType))}
            className={`${BTN_PRIMARY} px-[28px] py-[14px] text-[16px]`}
            aria-label={uiText("m09d9dcdba8c6431c")}
          >
            {uiText("m09d9dcdba8c6431c")}
          </button>
        </div>

        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-[16px]">
          <button
            type="button"
            onClick={() => router.push("/quiz_history")}
            className="flex flex-col items-start gap-[6px] border-2 border-divider bg-paper p-[20px] text-left transition hover:border-ink/60 hover:bg-ink/[0.02]"
            aria-label={uiText("mb71c498fac1d5339", { value0: t("report") })}
          >
            <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
              {uiText("m0e76960093379060")}
            </p>
            <p className="text-[15px] font-extrabold text-ink">
              {uiText("mb71c498fac1d5339", { value0: t("report") })}
            </p>
            <p className="text-[13.5px] leading-[20px] text-ink/70">
              {uiText("m081d71b1aa17d679", { value0: t("assignment") })}
            </p>
          </button>

          <button
            type="button"
            onClick={() => router.push("/quiz_history")}
            className="flex flex-col items-start gap-[6px] border-2 border-divider bg-paper p-[20px] text-left transition hover:border-ink/60 hover:bg-ink/[0.02]"
            aria-label={uiText("m3c331defca9c5dec")}
          >
            <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
              {uiText("m942087cc2d41e013")}
            </p>
            <p className="text-[15px] font-extrabold text-ink">
              {uiText("m3c331defca9c5dec")}
            </p>
            <p className="text-[13.5px] leading-[20px] text-ink/70">
              {uiText("m8c2340890eb7b8b4")}
            </p>
          </button>
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="student-presets-heading"
      >
        <Kicker>{uiText("m1aa90426a6a2701d")}</Kicker>
        <h2
          id="student-presets-heading"
          className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
        >
          {uiText("mfd5383c2f9a05cd0")}
        </h2>
        <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
          {uiText("m6cbd8fa167b45571")}
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
        aria-labelledby="student-live-heading"
      >
        <Kicker>{uiText("mfef250162a1277bb")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="student-live-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("m685866fd1f176bb7", { value0: t("session") })}
            </h2>
            <p className="mt-[6px] max-w-[56ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("m42df97b56efda9c8", { value0: t("session") })}
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push("/quiz-access")}
            className={BTN_GHOST}
            aria-label={uiText("m21e31e177db66d84")}
          >
            {uiText("m21e31e177db66d84")}
          </button>
        </div>
      </section>
    </div>
  );
}
