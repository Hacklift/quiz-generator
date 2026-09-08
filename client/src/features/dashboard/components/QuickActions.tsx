"use client";

import React from "react";
import { useRouter } from "next/router";

interface QuickActionBase {
  label: string;
  description: string;
}

export type QuickAction =
  | (QuickActionBase & { href: string; unavailable?: never })
  | (QuickActionBase & { href?: never; unavailable: true });

/**
 * [SCAFFOLD-OWNED] Row of primary entry points at the top of a dashboard.
 * Category dashboards supply the actions; the layout stays consistent.
 */
export default function QuickActions({ actions }: { actions: QuickAction[] }) {
  const router = useRouter();

  return (
    <section>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-[24px]">
        {actions.map((action) => (
          <button
            key={action.label}
            type="button"
            onClick={() => {
              if (!action.unavailable) router.push(action.href);
            }}
            disabled={action.unavailable}
            className="border-t-2 border-divider px-[6px] py-[20px] text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:bg-transparent"
          >
            <span className="flex items-start gap-[14px]">
              <span className="mt-[6px] h-[8px] w-[8px] flex-none bg-brand" />
              <span className="flex-1">
                <span className="block text-[17px] font-extrabold leading-[1.2]">
                  {action.label}
                </span>
                <span className="mt-[4px] block text-[13.5px] leading-[22px] text-ink/70">
                  {action.description}
                </span>
                {action.unavailable ? (
                  <span className="mt-[8px] block text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
                    Coming soon
                  </span>
                ) : null}
              </span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
