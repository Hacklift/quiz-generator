"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import {
  liveQuizService,
  type LiveQuizAttemptDetail,
} from "@features/live-quiz/api/liveQuizService";
import { archivo, CONTAINER, Kicker } from "@shared/ui/quizwerk";

export default function LiveQuizAttemptDetailPage({
  quizId,
  sessionId,
}: {
  quizId: string;
  sessionId: string;
}) {
  const { t: uiText } = useTranslation("ui");

  const [attempt, setAttempt] = useState<LiveQuizAttemptDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    liveQuizService
      .getAttemptDetail(quizId, sessionId)
      .then((data) => {
        if (active) setAttempt(data);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError?.response?.status === 403) {
          setError(uiText("mfe5eeb1d66d9e431"));
        } else if (requestError?.response?.status === 409) {
          setError(uiText("m8e0cdebe870ee958"));
        } else {
          setError(uiText("mb4d3ded0727ed897"));
        }
      });
    return () => {
      active = false;
    };
  }, [quizId, sessionId]);

  return (
    <RequireAuth
      title={uiText("m157c297f19a2fc2c")}
      description={uiText("mb5dd5705bb97ce67")}
    >
      <div
        className={`${archivo.className} flex min-h-screen flex-col bg-paper text-ink`}
      >
        <NavBar />
        <main className={`${CONTAINER} flex-grow py-[clamp(32px,5vw,56px)]`}>
          {error ? (
            <p
              role="alert"
              className="border-t-2 border-divider pt-[24px] text-red-700"
            >
              {error}
            </p>
          ) : !attempt ? (
            <p>{uiText("mcf2c63891e329852")}</p>
          ) : (
            <>
              <Kicker>{uiText("m1de191113fc61a56")}</Kicker>
              <h1 className="text-[clamp(28px,4vw,40px)] font-extrabold">
                {attempt.title}
              </h1>
              <p className="mt-[8px] text-ink/70">{attempt.participant_name}</p>
              <div className="mt-[26px] grid gap-[14px] sm:grid-cols-2">
                <div className="border-t-2 border-divider pt-[14px]">
                  <span className="block text-[12px] font-extrabold uppercase tracking-[0.08em] text-ink/60">
                    {uiText("m38e5a46cbc5ad328")}
                  </span>
                  <strong className="mt-[4px] block text-[30px]">
                    {attempt.score}/{attempt.total_questions}
                  </strong>
                </div>
                <div className="border-t-2 border-divider pt-[14px]">
                  <span className="block text-[12px] font-extrabold uppercase tracking-[0.08em] text-ink/60">
                    {uiText("m379db318f5b44fcd")}
                  </span>
                  <strong className="mt-[4px] block text-[30px]">
                    {attempt.percentage}%
                  </strong>
                </div>
              </div>
              <section className="mt-[34px]">
                <h2 className="text-[20px] font-extrabold">
                  {uiText("m32426840309c396e")}
                </h2>
                <ol className="mt-[12px]">
                  {attempt.graded_answers.map((answer) => (
                    <li
                      key={answer.question_index}
                      className="border-t-2 border-divider py-[16px]"
                    >
                      <div className="flex items-start gap-[12px]">
                        <span
                          aria-label={
                            answer.is_correct ? "Correct" : "Incorrect"
                          }
                          className={`text-[20px] font-extrabold ${answer.is_correct ? "text-green-700" : "text-red-700"}`}
                        >
                          {answer.is_correct ? "✓" : "✗"}
                        </span>
                        <div>
                          <h3 className="font-extrabold">
                            {uiText("m289aff12b04274cb")}
                            {answer.question_index + 1}
                          </h3>
                          <p className="mt-[5px]">{answer.question}</p>
                          <p className="mt-[8px] text-[14px] text-ink/70">
                            {uiText("m23451c00f3856491")}
                            {answer.selected_answer ||
                              uiText("m7e49c68db30e39dc")}
                          </p>
                          <p className="mt-[3px] text-[14px] text-ink/70">
                            {uiText("m4d659fb1085d715b")}
                            {answer.correct_answer}
                          </p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
              <Link
                href={`/my-live-quizzes/${quizId}`}
                className="mt-[24px] inline-block font-extrabold text-brand underline"
              >
                {uiText("m4b8605aa294a9f66")}
              </Link>
            </>
          )}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
