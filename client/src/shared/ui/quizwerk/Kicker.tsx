import React from "react";

/** Small uppercase section label. `onPaper` = rendered inside a navy field. */
export default function Kicker({
  children,
  onPaper = false,
}: {
  children: React.ReactNode;
  onPaper?: boolean;
}) {
  return (
    <p
      className={`mb-[16px] text-[13px] font-extrabold uppercase tracking-[0.08em] ${
        onPaper ? "text-brand-200" : "text-brand-700"
      }`}
    >
      {children}
    </p>
  );
}
