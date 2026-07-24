import React from "react";

/**
 * Decorative laptop + phone mockup for the hero (design_handoff_home_page §2).
 * Pure HTML/CSS — the only rounded corners in the design are device hardware.
 */

function AnswerRow({
  letter,
  text,
  pct,
  leader,
}: {
  letter: string;
  text: string;
  pct: number;
  leader?: boolean;
}) {
  return (
    <div className="mb-[10px]">
      <div className="flex items-baseline justify-between text-[12px] leading-[1.3]">
        <span>
          <span className="font-extrabold">{letter}</span> {text}
        </span>
        <span className="[font-variant-numeric:tabular-nums] text-ink/70">
          {pct}%
        </span>
      </div>
      <div className="mt-[4px] h-[8px] w-full bg-[#e4e3e2]">
        <div
          className={leader ? "h-full bg-brand" : "h-full bg-brand-300"}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function HeroMockup() {
  return (
    <div aria-hidden="true" className="relative mr-[96px] pb-[28px] max-[560px]:mr-0">
      {/* ── Laptop ── */}
      <div>
        {/* Screen bezel */}
        <div className="rounded-t-[16px] bg-[#101012] p-[10px] pb-0">
          <div className="mx-auto mb-[6px] h-[6px] w-[6px] rounded-full bg-[#2a2a2e]" />
          {/* Screen — presenter view */}
          <div className="bg-paper p-[18px] pr-[80px] text-ink">
            <div className="flex items-center justify-between pb-[8px]">
              <span className="flex items-center gap-[7px] text-[11px] font-extrabold uppercase tracking-[0.1em] text-brand-700">
                <span className="h-[7px] w-[7px] animate-live-pulse bg-brand" />
                LIVE · 4F7KQ2
              </span>
              <span className="text-[11px] [font-variant-numeric:tabular-nums] text-ink/70">
                3 / 5
              </span>
            </div>
            <div className="mb-[12px] h-[2px] bg-divider" />
            <p className="mb-[12px] font-extrabold leading-[1.25] tracking-[-0.015em] text-[16px]">
              Which of these is the correct first step in a fire evacuation?
            </p>
            <AnswerRow letter="A" text="Raise the alarm" pct={62} leader />
            <AnswerRow letter="B" text="Collect belongings" pct={21} />
            <AnswerRow letter="C" text="Call your manager" pct={17} />
            <p className="mt-[12px] text-[11px] uppercase tracking-[0.08em] text-ink/50">
              24 of 26 answered
            </p>
          </div>
        </div>
        {/* Aluminum base bar */}
        <div className="relative h-[14px] rounded-b-[12px] bg-gradient-to-b from-[#e4e4e8] to-[#b6b6bd]">
          <div className="absolute left-1/2 top-0 h-[5px] w-[86px] -translate-x-1/2 rounded-b-[6px] bg-[#a9a9b1]" />
        </div>
      </div>

      {/* ── Phone — participant view ── */}
      <div className="absolute bottom-0 right-0 w-[164px] rounded-[28px] bg-[#101012] p-[7px] max-[560px]:relative max-[560px]:mx-auto max-[560px]:mt-[16px]">
        <div className="rounded-[21px] bg-paper px-[12px] pb-[10px] pt-[8px] text-ink">
          <div className="mx-auto mb-[8px] h-[16px] w-[54px] rounded-full bg-[#101012]" />
          <p className="mb-[6px] flex items-center gap-[5px] text-[9px] font-extrabold uppercase tracking-[0.1em] text-brand-700">
            <span className="h-[5px] w-[5px] animate-live-pulse bg-brand" />
            LIVE
          </p>
          <p className="mb-[8px] text-[11px] font-extrabold leading-[1.3] tracking-[-0.015em]">
            Which of these is the correct first step in a fire evacuation?
          </p>
          <div className="mb-[6px] border-[1.5px] border-brand bg-brand-100 px-[8px] py-[6px] text-[10px]">
            <span className="font-extrabold">A</span> Raise the alarm
          </div>
          <div className="mb-[6px] border-[1.5px] border-divider px-[8px] py-[6px] text-[10px]">
            <span className="font-extrabold">B</span> Collect belongings
          </div>
          <div className="mb-[8px] border-[1.5px] border-divider px-[8px] py-[6px] text-[10px]">
            <span className="font-extrabold">C</span> Call your manager
          </div>
          <div className="bg-brand px-[8px] py-[7px] text-center text-[11px] font-extrabold text-paper">
            Submit
          </div>
          <div className="mx-auto mt-[8px] h-[3px] w-[48px] rounded-full bg-[#101012]/30" />
        </div>
      </div>
    </div>
  );
}
