import React from "react";
import { getUserTypeDefinition } from "@shared/config/persona";
import type { DashboardViewProps } from "@features/dashboard/types/dashboard";

/**
 * [SCAFFOLD-OWNED] What an unbuilt persona view renders.
 *
 * Keeps every route real and navigable while its ticket is open, and tells
 * whoever lands here which issue owns the work.
 */
export default function DashboardPlaceholder({
  issue,
  title,
  persona,
}: {
  issue: number;
  title: string;
  persona: DashboardViewProps["persona"];
}) {
  const definition = getUserTypeDefinition(persona.userType);

  return (
    <section className="border-t-2 border-divider pt-[28px]">
      <p className="mb-[10px] text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
        In progress
      </p>
      <h2 className="text-[24px] font-extrabold leading-[1.12] tracking-[-0.015em]">
        {title}
      </h2>
      <p className="mt-[12px] max-w-[52ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
        {definition.description}. This view is being built in issue #{issue} —
        until then, everything else in the app works as before.
      </p>
      <a
        href={`https://github.com/Hacklift/quiz-generator/issues/${issue}`}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-[20px] inline-flex items-center gap-[8px] text-[14px] font-extrabold text-brand-700 hover:text-brand"
      >
        <span className="h-[8px] w-[8px] bg-brand" aria-hidden="true" />
        Track issue #{issue}
      </a>
    </section>
  );
}
