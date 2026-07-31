import React from "react";
import { CONTAINER, Kicker } from "@shared/ui/quizwerk";

/**
 * [SCAFFOLD-OWNED] Page chrome shared by every persona view: kicker,
 * heading, optional lede, then the view's own content below a 2px seam.
 */
export default function DashboardShell({
  kicker,
  title,
  lede,
  actions,
  children,
}: {
  kicker: string;
  title: string;
  lede?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className={`${CONTAINER} py-[clamp(32px,5vw,56px)]`}>
      <header className="border-b-2 border-divider pb-[28px]">
        <Kicker>{kicker}</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[20px]">
          <div>
            <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
              {title}
            </h1>
            {lede ? (
              <p className="mt-[12px] max-w-[52ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
                {lede}
              </p>
            ) : null}
          </div>
          {actions ? (
            <div className="flex flex-wrap gap-[12px]">{actions}</div>
          ) : null}
        </div>
      </header>
      <div className="pt-[36px]">{children}</div>
    </div>
  );
}
