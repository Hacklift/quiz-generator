"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { getUserQuizHistory } from "@features/quiz-history/api/quizHistoryApi";

interface HistoryRow {
  _id?: string;
  id?: string;
  quiz_title?: string | null;
  score?: number;
  total_questions?: number;
  percentage?: number;
  submitted_at?: string;
}

/**
 * [SCAFFOLD-OWNED] Recent activity list, read from graded attempts so the
 * dashboard reflects scored practice history.
 */
export default function RecentQuizzes({
  heading,
  emptyMessage,
  limit = 5,
}: {
  heading: string;
  emptyMessage: string;
  limit?: number;
}) {
  const router = useRouter();
  const [rows, setRows] = useState<HistoryRow[] | null>(null);

  useEffect(() => {
    let active = true;
    getUserQuizHistory().then((history) => {
      if (active)
        setRows(Array.isArray(history) ? history.slice(0, limit) : []);
    });
    return () => {
      active = false;
    };
  }, [limit]);

  return (
    <section className="border-t-2 border-divider pt-[28px]">
      <h2 className="text-[20px] font-extrabold tracking-[-0.015em]">
        {heading}
      </h2>

      {rows === null ? (
        <p className="mt-[14px] text-[14px] text-ink/60">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="mt-[14px] max-w-[52ch] text-[15px] leading-[26px] text-ink/70">
          {emptyMessage}
        </p>
      ) : (
        <ul className="mt-[14px]">
          {rows.map((row) => {
            const id = row._id || row.id || "";
            return (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => router.push(`/quiz_history/${id}`)}
                  className="flex w-full flex-wrap items-baseline justify-between gap-[12px] border-t-2 border-divider px-[6px] py-[14px] text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
                >
                  <span className="text-[15px] font-extrabold">
                    {row.quiz_title || "Untitled quiz"}
                  </span>
                  <span className="text-[13px] text-ink/60">
                    {typeof row.score === "number" &&
                    typeof row.total_questions === "number"
                      ? `Score ${row.score}/${row.total_questions}`
                      : "Attempt"}
                    {typeof row.percentage === "number"
                      ? ` · ${row.percentage.toFixed(0)}%`
                      : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
