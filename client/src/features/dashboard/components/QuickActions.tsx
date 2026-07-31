"use client";

import React from "react";
import { useRouter } from "next/router";

export interface QuickAction {
  label: string;
  description: string;
  href: string;
}

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
            onClick={() => router.push(action.href)}
            className="border-t-2 border-divider px-[6px] py-[20px] text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
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
              </span>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
