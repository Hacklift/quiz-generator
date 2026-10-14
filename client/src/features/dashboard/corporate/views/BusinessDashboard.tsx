"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import {
  trainingRunApi,
  type TrainingRunSummary,
} from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { personaGenerateHref } from "@shared/config/persona";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";
import { ROUTES } from "@shared/config/patterns/routes";

const formatDate = (value?: string | null) =>
  value ? new Date(value).toLocaleDateString() : "No deadline";
const completionLabel = (run: TrainingRunSummary) =>
  run.assigned_count
    ? `${run.completed_count}/${run.assigned_count} complete`
    : `${run.completed_count} completed`;

const businessPresetHref = (
  userType: DashboardViewProps["persona"]["userType"],
  preset: "onboarding" | "product-knowledge",
) => {
  const params = new URLSearchParams(
    personaGenerateHref(userType).split("?")[1],
  );
  if (preset === "onboarding") {
    params.set("topic", "Employee onboarding essentials");
    params.set(
      "customInstruction",
      "Create practical first-week onboarding checks for employees.",
    );
  } else {
    params.set("topic", "Product knowledge");
    params.set(
      "customInstruction",
      "Test practical product knowledge for customer-facing teams.",
    );
  }
  return `/generate?${params.toString()}`;
};

export default function BusinessDashboard({ persona }: DashboardViewProps) {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const t = useTerms();
  const [runs, setRuns] = useState<TrainingRunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    void trainingRunApi
      .listRuns()
      .then((items) => {
        if (!active) return;
        setRuns(items);
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

  const presets = [
    {
      id: "onboarding",
      title: uiText("m73f7c68653183f09"),
      description: uiText("mf553482d4b2e759b", {
        value0: t("quiz"),
        value1: t("group", "plural"),
      }),
    },
    {
      id: "product-knowledge",
      title: uiText("mbe7077604d1d8f33"),
      description: uiText("mefbe30179911363b", {
        value0: t("group", "plural"),
      }),
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="business-presets-heading"
      >
        <Kicker>{uiText("m6fa61dd8f4d0ed00")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="business-presets-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("m62a991bbf7eed5ec")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("mbd24087608269ab4")}
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.push(`${ROUTES.TRAINING_RUNS}?kind=business`)}
            className={BTN_PRIMARY}
          >
            {uiText("maebcad530db03bee")}
          </button>
        </div>
        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[20px]">
          {presets.map((preset) => (
            <article
              key={preset.id}
              className="flex flex-col justify-between border-2 border-divider bg-paper p-[20px]"
            >
              <div>
                <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
                  {uiText("m212442d21c636906")}
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
                onClick={() =>
                  router.push(
                    businessPresetHref(
                      persona.userType,
                      preset.id as "onboarding" | "product-knowledge",
                    ),
                  )
                }
                className={`${BTN_PRIMARY} mt-[20px] w-full`}
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
        aria-labelledby="business-runs-heading"
      >
        <Kicker>{uiText("m33741c714d192412")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="business-runs-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("m7445a62c0b670145")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("me8a534c98d4cf8be")}
              {t("session")}.
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.push(`${ROUTES.TRAINING_RUNS}?kind=business`)}
            className={BTN_GHOST}
          >
            {uiText("m346de5a03a7af536")}
          </button>
        </div>
        {isLoading ? (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] text-ink/70">
            {uiText("md11ca191e75a7f25")}
          </p>
        ) : loadError ? (
          <p
            role="alert"
            className="mt-[20px] border-2 border-brand bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70"
          >
            {uiText("ma6db1d54dee2cb3a")}
          </p>
        ) : runs.length ? (
          <div className="mt-[20px] grid gap-[12px]">
            {runs.slice(0, 3).map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => router.push(ROUTES.trainingRun(run.id))}
                className="grid w-full grid-cols-1 gap-[12px] border-2 border-divider bg-paper p-[16px] text-left transition hover:border-ink/60 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center"
              >
                <span>
                  <strong className="block text-ink">{run.title}</strong>
                  <span className="mt-[3px] block text-[13px] text-ink/65">
                    {uiText("m74c21a6312ede178")}
                    {formatDate(run.closes_at)}
                  </span>
                </span>
                <span className="text-[13px] font-extrabold text-ink">
                  {completionLabel(run)}
                </span>
                <span className="text-[13px] text-ink/70">
                  {run.average_score ?? "-"} {uiText("mb04eecaff03bcdd1")}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
            {uiText("m10f6e507278345cd")}
            {t("group", "plural")} {uiText("mc3302962dcfeb27c")}
          </p>
        )}
      </section>
    </div>
  );
}
