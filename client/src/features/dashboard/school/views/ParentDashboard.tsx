"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTerms } from "@features/persona/hooks/useTerms";
import {
  liveQuizService,
  type LiveQuizSummary,
} from "@features/live-quiz/api/liveQuizService";
import { BTN_PRIMARY } from "@shared/ui/quizwerk";

export default function ParentDashboard() {
  const t = useTerms();
  const [practices, setPractices] = useState<LiveQuizSummary[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    liveQuizService
      .listLiveQuizzes()
      .then((rows) => {
        if (active) setPractices(rows.slice(0, 5));
      })
      .catch(() => {
        if (active) {
          setError(true);
          setPractices([]);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="border-t-2 border-divider pt-[28px]">
      <div className="flex flex-wrap items-end justify-between gap-[18px]">
        <div>
          <h2 className="text-[20px] font-extrabold tracking-[-0.015em]">
            Parent dashboard
          </h2>
          <p className="mt-[7px] text-[14px] text-ink/70">
            Create an automatically marked {t("assignment")} for your {t("learner")}.
          </p>
        </div>
        <Link href="/parent-practice/new" className={BTN_PRIMARY}>
          Create Practice
        </Link>
      </div>

      <h3 className="mt-[32px] text-[17px] font-extrabold">Recent practice</h3>
      {practices === null ? (
        <p className="mt-[14px] text-[14px] text-ink/60">Loading…</p>
      ) : error ? (
        <p className="mt-[14px] text-[14px] text-red-700">
          Recent practice could not be loaded.
        </p>
      ) : practices.length === 0 ? (
        <p className="mt-[14px] text-[14px] text-ink/70">
          No practice yet. Create the first set when you are ready.
        </p>
      ) : (
        <ul className="mt-[12px]">
          {practices.map((practice) => (
            <li key={practice.quiz_id} className="border-t-2 border-divider py-[16px]">
              <div className="flex flex-wrap items-center justify-between gap-[14px]">
                <div>
                  <p className="font-extrabold">{practice.title}</p>
                  <p className="mt-[4px] text-[13px] text-ink/65">
                    {practice.completed_count} completed {practice.completed_count === 1 ? "attempt" : "attempts"}
                    {practice.latest_score != null
                      ? ` · Latest: ${practice.latest_score}${practice.latest_percentage != null ? ` (${practice.latest_percentage}%)` : ""}`
                      : ""}
                  </p>
                </div>
                <Link className="text-[14px] font-extrabold text-brand underline" href={`/my-live-quizzes/${practice.quiz_id}`}>
                  View results
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
