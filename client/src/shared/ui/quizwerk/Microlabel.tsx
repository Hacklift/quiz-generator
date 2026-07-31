import React from "react";

/** Tiny uppercase label above a value or panel. */
export default function Microlabel({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <p className="mb-[10px] text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
      {children}
    </p>
  );
}
