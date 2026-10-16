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

const compliancePresetHref = (
  userType: DashboardViewProps["persona"]["userType"],
  preset: "harassment-prevention" | "health-and-safety",
) => {
  const params = new URLSearchParams(
    personaGenerateHref(userType).split("?")[1],
  );
  if (preset === "harassment-prevention") {
    params.set("topic", "Workplace harassment prevention");
    params.set(
      "customInstruction",
      "Use scenario-based compliance checks with clear policy language.",
    );
  } else {
    params.set("topic", "Workplace health and safety");
    params.set(
      "customInstruction",
      "Use practical health and safety scenarios and clear compliance checks.",
    );
  }
  return `/generate?${params.toString()}`;
};

export default function HrDashboard({ persona }: DashboardViewProps) {
  const { t: uiText, i18n } = useTranslation("ui");

  const completionLabel = (run: TrainingRunSummary) =>
    run.assigned_count
      ? uiText("trainingStatus.progress", {
          completed: run.completed_count,
          total: run.assigned_count,
        })
      : uiText("trainingStatus.completed", { completed: run.completed_count });

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
        setRuns(items.filter((run) => run.kind === "compliance"));
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
    ["harassment-prevention", uiText("trainingStatus.harassment")],
    ["health-and-safety", uiText("trainingStatus.safety")],
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="hr-presets-heading"
      >
        <Kicker>{uiText("mf7d49050021cb6b2")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="hr-presets-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("me21e2e7fd7635c1c")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("m7515715d63e370ff", { value0: t("group", "plural") })}
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              router.push(`${ROUTES.TRAINING_RUNS}?kind=compliance`)
            }
            className={BTN_PRIMARY}
          >
            {uiText("mf5ab22f82138a2cf")}
          </button>
        </div>
        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[20px]">
          {presets.map(([id, title]) => (
            <article
              key={id}
              className="flex flex-col justify-between border-2 border-divider bg-paper p-[20px]"
            >
              <div>
                <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">
                  {uiText("ma224402dec844c84")}
                </p>
                <h3 className="mt-[10px] text-[17px] font-extrabold text-ink">
                  {title}
                </h3>
                <p className="mt-[8px] text-[13.5px] leading-[22px] text-ink/70">
                  {uiText("m30753c8aac022ff3", { value0: t("quiz") })}
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  router.push(
                    compliancePresetHref(
                      persona.userType,
                      id as "harassment-prevention" | "health-and-safety",
                    ),
                  )
                }
                className={`${BTN_PRIMARY} mt-[20px] w-full`}
              >
                {uiText("m37a7e45e1b49df1f", { value0: title })}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section
        className="border-t-2 border-divider pt-[28px]"
        aria-labelledby="hr-register-heading"
      >
        <Kicker>{uiText("m70db1427b3006d6a")}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2
              id="hr-register-heading"
              className="text-[20px] font-extrabold tracking-[-0.015em] text-ink"
            >
              {uiText("ma2a37cdc182ccdfe")}
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              {uiText("m6aea24e1c7bd01d8")}
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              router.push(`${ROUTES.TRAINING_RUNS}?kind=compliance`)
            }
            className={BTN_GHOST}
          >
            {uiText("md229758ee84eb51d")}
          </button>
        </div>
        {isLoading ? (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] text-ink/70">
            {uiText("m666dea31fa313379")}
          </p>
        ) : loadError ? (
          <p
            role="alert"
            className="mt-[20px] border-2 border-brand bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70"
          >
            {uiText("m34c43078a620173f")}
          </p>
        ) : runs.length ? (
          <div className="mt-[20px] grid gap-[12px]">
            {runs.slice(0, 3).map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => router.push(ROUTES.trainingRun(run.id))}
                className="grid w-full grid-cols-1 gap-[10px] border-2 border-divider bg-paper p-[16px] text-left transition hover:border-ink/60 sm:grid-cols-[minmax(0,1fr)_auto_auto]"
              >
                <span>
                  <strong className="block text-ink">{run.title}</strong>
                  <span className="mt-[3px] block text-[13px] text-ink/65">
                    {run.status === "closed"
                      ? uiText("mca6acc608c0f03c0")
                      : uiText("mdb8084b091623bcc", {
                          value0: new Date(run.closes_at).toLocaleDateString(
                            i18n.language,
                          ),
                        })}
                  </span>
                </span>
                <span className="text-[13px] font-extrabold text-ink">
                  {completionLabel(run)}
                </span>
                <span className="text-[13px] text-ink/70">
                  {uiText("mfff86921b49f612d", {
                    value0: run.average_score ?? "-",
                  })}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
            {uiText("ma8efb06992552503", {
              value0: t("quiz"),
              value1: t("group", "plural"),
            })}
          </p>
        )}
      </section>
    </div>
  );
}
