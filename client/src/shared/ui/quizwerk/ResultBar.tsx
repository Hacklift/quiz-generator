import React from "react";

/** Labelled horizontal bar — question id, fill, percentage. */
export default function ResultBar({
  q,
  pct,
  tone,
}: {
  q: string;
  pct: number;
  tone: "brand" | "brand-300";
}) {
  return (
    <div className="mb-[10px] flex items-center gap-[10px]">
      <span className="w-[26px] text-[12px] font-extrabold">{q}</span>
      <div className="h-[10px] flex-1 bg-[#e4e3e2]">
        <div
          className={tone === "brand" ? "h-full bg-brand" : "h-full bg-brand-300"}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-[40px] text-right text-[12px] [font-variant-numeric:tabular-nums] text-ink/70">
        {pct}%
      </span>
    </div>
  );
}
