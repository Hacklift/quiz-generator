"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useTerms } from "@features/persona/hooks/useTerms";
import { trainingRunApi, type TrainingRunSummary } from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { personaGenerateHref } from "@shared/config/persona";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

const completionLabel = (run: TrainingRunSummary) =>
  run.assigned_count
    ? `${run.completed_count}/${run.assigned_count} complete`
    : `${run.completed_count} completed`;

const compliancePresetHref = (
  userType: DashboardViewProps["persona"]["userType"],
  preset: "harassment-prevention" | "health-and-safety",
) => {
  const params = new URLSearchParams(
    personaGenerateHref(userType).split("?")[1],
  );
  if (preset === "harassment-prevention") {
    params.set("topic", "Workplace harassment prevention");
    params.set("customInstruction", "Use scenario-based compliance checks with clear policy language.");
  } else {
    params.set("topic", "Workplace health and safety");
    params.set("customInstruction", "Use practical health and safety scenarios and clear compliance checks.");
  }
  return `/generate?${params.toString()}`;
};

export default function HrDashboard({ persona }: DashboardViewProps) {
  const router = useRouter();
  const t = useTerms();
  const [runs, setRuns] = useState<TrainingRunSummary[]>([]);

  useEffect(() => {
    void trainingRunApi
      .listRuns()
      .then((items) => setRuns(items.filter((run) => run.kind === "compliance")))
      .catch(() => setRuns([]));
  }, []);

  const presets = [
    ["harassment-prevention", "Harassment prevention"],
    ["health-and-safety", "Health & safety"],
  ];

  return (
    <div className="flex flex-col gap-[36px]">
      <section className="border-t-2 border-divider pt-[28px]" aria-labelledby="hr-presets-heading">
        <Kicker>HR personnel dashboard</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2 id="hr-presets-heading" className="text-[20px] font-extrabold tracking-[-0.015em] text-ink">Compliance training runs</h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">
              Create required training, assign it to your {t("group", "plural")}, and close a verifiable completion register.
            </p>
          </div>
          <button type="button" onClick={() => router.push("/training-runs?kind=compliance")} className={BTN_PRIMARY}>Create compliance run</button>
        </div>
        <div className="mt-[20px] grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-[20px]">
          {presets.map(([id, title]) => (
            <article key={id} className="flex flex-col justify-between border-2 border-divider bg-paper p-[20px]">
              <div>
                <p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">Compliance preset</p>
                <h3 className="mt-[10px] text-[17px] font-extrabold text-ink">{title}</h3>
                <p className="mt-[8px] text-[13.5px] leading-[22px] text-ink/70">Generate a marked training {t("quiz")} and record completion by person, date, and score.</p>
              </div>
              <button type="button" onClick={() => router.push(compliancePresetHref(persona.userType, id as "harassment-prevention" | "health-and-safety"))} className={`${BTN_PRIMARY} mt-[20px] w-full`}>Create {title}</button>
            </article>
          ))}
        </div>
      </section>

      <section className="border-t-2 border-divider pt-[28px]" aria-labelledby="hr-register-heading">
        <Kicker>Completion register</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div>
            <h2 id="hr-register-heading" className="text-[20px] font-extrabold tracking-[-0.015em] text-ink">Active and closed records</h2>
            <p className="mt-[6px] max-w-[58ch] text-[14.5px] leading-[24px] text-ink/70">Open a run to review who completed it, when they submitted, and their score. Closing preserves the final register.</p>
          </div>
          <button type="button" onClick={() => router.push("/training-runs?kind=compliance")} className={BTN_GHOST}>View compliance runs</button>
        </div>
        {runs.length ? (
          <div className="mt-[20px] grid gap-[12px]">
            {runs.slice(0, 3).map((run) => (
              <button key={run.id} type="button" onClick={() => router.push(`/training-runs/${run.id}`)} className="grid w-full grid-cols-1 gap-[10px] border-2 border-divider bg-paper p-[16px] text-left transition hover:border-ink/60 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
                <span><strong className="block text-ink">{run.title}</strong><span className="mt-[3px] block text-[13px] text-ink/65">{run.status === "closed" ? "Closed record" : `Closes ${new Date(run.closes_at).toLocaleDateString()}`}</span></span>
                <span className="text-[13px] font-extrabold text-ink">{completionLabel(run)}</span>
                <span className="text-[13px] text-ink/70">{run.average_score ?? "-"} avg score</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="mt-[20px] border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">No compliance runs yet. Start from a preset, then assign the completed {t("quiz")} to your {t("group", "plural")}.</p>
        )}
      </section>
    </div>
  );
}
