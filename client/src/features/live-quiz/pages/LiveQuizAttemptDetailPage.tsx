"use client";

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
          setError("You are not allowed to view this attempt.");
        } else if (requestError?.response?.status === 409) {
          setError("This attempt has not been completed yet.");
        } else {
          setError("Attempt results could not be found.");
        }
      });
    return () => {
      active = false;
    };
  }, [quizId, sessionId]);

  return (
    <RequireAuth title="Results sign-in required" description="Sign in to view these results.">
      <div className={`${archivo.className} flex min-h-screen flex-col bg-paper text-ink`}>
        <NavBar />
        <main className={`${CONTAINER} flex-grow py-[clamp(32px,5vw,56px)]`}>
          {error ? (
            <p role="alert" className="border-t-2 border-divider pt-[24px] text-red-700">{error}</p>
          ) : !attempt ? (
            <p>Loading results…</p>
          ) : (
            <>
              <Kicker>Completed attempt</Kicker>
              <h1 className="text-[clamp(28px,4vw,40px)] font-extrabold">{attempt.title}</h1>
              <p className="mt-[8px] text-ink/70">{attempt.participant_name}</p>
              <div className="mt-[26px] grid gap-[14px] sm:grid-cols-2">
                <div className="border-t-2 border-divider pt-[14px]">
                  <span className="block text-[12px] font-extrabold uppercase tracking-[0.08em] text-ink/60">Score</span>
                  <strong className="mt-[4px] block text-[30px]">{attempt.score}/{attempt.total_questions}</strong>
                </div>
                <div className="border-t-2 border-divider pt-[14px]">
                  <span className="block text-[12px] font-extrabold uppercase tracking-[0.08em] text-ink/60">Percentage</span>
                  <strong className="mt-[4px] block text-[30px]">{attempt.percentage}%</strong>
                </div>
              </div>
              <section className="mt-[34px]">
                <h2 className="text-[20px] font-extrabold">Question results</h2>
                <ol className="mt-[12px]">
                  {attempt.graded_answers.map((answer) => (
                    <li key={answer.question_index} className="border-t-2 border-divider py-[16px]">
                      <div className="flex items-start gap-[12px]">
                        <span aria-label={answer.is_correct ? "Correct" : "Incorrect"} className={`text-[20px] font-extrabold ${answer.is_correct ? "text-green-700" : "text-red-700"}`}>
                          {answer.is_correct ? "✓" : "✗"}
                        </span>
                        <div>
                          <h3 className="font-extrabold">Question {answer.question_index + 1}</h3>
                          <p className="mt-[5px]">{answer.question}</p>
                          <p className="mt-[8px] text-[14px] text-ink/70">Child&apos;s answer: {answer.selected_answer || "No answer"}</p>
                          <p className="mt-[3px] text-[14px] text-ink/70">Correct answer: {answer.correct_answer}</p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
              <Link href={`/my-live-quizzes/${quizId}`} className="mt-[24px] inline-block font-extrabold text-brand underline">Back to attempts</Link>
            </>
          )}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
