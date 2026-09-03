"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import { trainingRunApi, type TrainingRunSummary } from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { personaGenerateHref } from "@shared/config/persona";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

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
    params.set("customInstruction", "Create practical first-week onboarding checks for employees.");
  } else {
    params.set("topic", "Product knowledge");
    params.set("customInstruction", "Test practical product knowledge for customer-facing teams.");
  }
  return `/generate?${params.toString()}`;
};

export default function BusinessDashboard({ persona }: DashboardViewProps) {
  const router = useRouter();
  const t = useTerms();
  const [runs, setRuns] = useState<TrainingRunSummary[]>([]);

  useEffect(() => {
    void trainingRunApi.listRuns().then(setRuns).catch(() => setRuns([]));
  }, []);

  const presets = [
    {
      id: "onboarding",
      title: "Employee onboarding",
      description: `Build a practical first-week ${t("quiz")} that gets new ${t("group", "plural")} aligned quickly.`,
    },
    {
      id: "product-knowledge",
      title: "Product knowledge",
      description: `Check that customer-facing ${t("group", "plural")} can explain the product with confidence.`,
    },
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section className="border-t-2 border-divider pt-[28px]" aria-labelledby="business-presets-heading">
        <Kicker>Business dashboard</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2 id="business-presets-heading" className="text-[20px] font-extrabold tracking-[-0.015em] text-ink">
              Create training that scales
            </h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              Start with a focused preset, then distribute it through an assigned training run or a shareable live link.
            </p>
          </div>
          <button type="button" onClick={() => router.push("/training-runs?kind=business")} className={BTN_PRIMARY}>
            Manage training runs
          </button>
        </div>
        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[20px]">
          {presets.map((preset) => (
            <article key={preset.id} className="flex flex-col justify-between border-2 border-divider bg-paper p-[20px]">
              <div>
                <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">Training preset</p>
                <h3 className="mt-[10px] text-[17px] font-extrabold text-ink">{preset.title}</h3>
                <p className="mt-[8px] text-[13.5px] leading-[22px] text-ink/70">{preset.description}</p>
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
                Create {preset.title}
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="border-t-2 border-divider pt-[28px]" aria-labelledby="business-runs-heading">
        <Kicker>Completion overview</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2 id="business-runs-heading" className="text-[20px] font-extrabold tracking-[-0.015em] text-ink">Your training runs</h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              See who has started, completed, and needs a reminder without opening each {t("session")}.
            </p>
          </div>
          <button type="button" onClick={() => router.push("/training-runs?kind=business")} className={BTN_GHOST}>View all runs</button>
        </div>
        {runs.length ? (
          <div className="mt-[20px] grid gap-[12px]">
            {runs.slice(0, 3).map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => router.push(`/training-runs/${run.id}`)}
                className="grid w-full grid-cols-1 gap-[12px] border-2 border-divider bg-paper p-[16px] text-left transition hover:border-ink/60 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center"
              >
                <span><strong className="block text-ink">{run.title}</strong><span className="mt-[3px] block text-[13px] text-ink/65">Closes {formatDate(run.closes_at)}</span></span>
                <span className="text-[13px] font-extrabold text-ink">{completionLabel(run)}</span>
                <span className="text-[13px] text-ink/70">{run.average_score ?? "-"} avg score</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
            No training runs yet. Create a quiz, then assign it to your {t("group", "plural")} or share a live link.
          </p>
        )}
      </section>
    </div>
  );
}
