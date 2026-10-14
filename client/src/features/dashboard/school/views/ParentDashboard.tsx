"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useTerms } from "@features/persona/hooks/useTerms";
import {
  liveQuizService,
  type LiveQuizSummary,
} from "@features/live-quiz/api/liveQuizService";
import { BTN_PRIMARY } from "@shared/ui/quizwerk";

export default function ParentDashboard() {
  const { t: uiText } = useTranslation("ui");

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
            {uiText("me01e39a0c5482ffd")}
          </h2>
          <p className="mt-[7px] text-[14px] text-ink/70">
            {uiText("mb80e7fa0db25d9f1")}
            {t("assignment")} {uiText("m75b99b5e3a11e30b")}
            {t("learner")}.
          </p>
        </div>
        <Link href="/parent-practice/new" className={BTN_PRIMARY}>
          {uiText("m92c7e9ad52f12b83")}
        </Link>
      </div>

      <h3 className="mt-[32px] text-[17px] font-extrabold">
        {uiText("mf767e1242f0f01ee")}
      </h3>
      {practices === null ? (
        <p className="mt-[14px] text-[14px] text-ink/60">
          {uiText("mba3bbbe10d8bef66")}
        </p>
      ) : error ? (
        <p className="mt-[14px] text-[14px] text-red-700">
          {uiText("meef47abc0c5f279a")}
        </p>
      ) : practices.length === 0 ? (
        <p className="mt-[14px] text-[14px] text-ink/70">
          {uiText("m455d5eacec795d96")}
        </p>
      ) : (
        <ul className="mt-[12px]">
          {practices.map((practice) => (
            <li
              key={practice.quiz_id}
              className="border-t-2 border-divider py-[16px]"
            >
              <div className="flex flex-wrap items-center justify-between gap-[14px]">
                <div>
                  <p className="font-extrabold">{practice.title}</p>
                  <p className="mt-[4px] text-[13px] text-ink/65">
                    {practice.completed_count} {uiText("m4ddb3e96801a1ee2")}
                    {practice.completed_count === 1
                      ? uiText("mc7ce66d0fb14e3c2")
                      : uiText("m1ac7d61d1d29fc2e")}
                    {practice.latest_score != null
                      ? ` · Latest: ${practice.latest_score}${practice.latest_percentage != null ? ` (${practice.latest_percentage}%)` : ""}`
                      : ""}
                  </p>
                </div>
                <Link
                  className="text-[14px] font-extrabold text-brand underline"
                  href={`/my-live-quizzes/${practice.quiz_id}`}
                >
                  {uiText("mf26efd3574998b71")}
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
