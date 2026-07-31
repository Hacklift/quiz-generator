import React from "react";

/** Numbered feature row: index, text block, and a flat vignette panel. */
export default function FeatureRow({
  n,
  title,
  copy,
  vignette,
}: {
  n: string;
  title: string;
  copy: string;
  vignette: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start gap-x-[48px] gap-y-[28px] border-t-2 border-divider py-[42px]">
      <span className="text-[15px] font-extrabold [font-variant-numeric:tabular-nums]">
        {n}
      </span>
      <div className="min-w-[260px] flex-1">
        <h3 className="mb-[10px] text-[24px] font-extrabold leading-[1.12] tracking-[-0.015em]">
          {title}
        </h3>
        <p className="max-w-[52ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
          {copy}
        </p>
      </div>
      <div className="w-full max-w-[420px] border-2 border-divider p-[20px]">
        {vignette}
      </div>
    </div>
  );
}
