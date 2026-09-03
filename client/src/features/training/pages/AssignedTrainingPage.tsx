"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";
import { trainingRunApi, type TrainingAssignment } from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, CONTAINER, Kicker } from "@shared/ui/quizwerk";

const stateLabel = (assignment: TrainingAssignment) => {
  if (assignment.status === "completed") return `Completed${assignment.latest_percentage != null ? ` · ${assignment.latest_percentage}%` : ""}`;
  if (new Date(assignment.latest_start_at) < new Date()) return "Start window closed";
  if (assignment.is_overdue) return "Overdue";
  return assignment.due_at ? `Due ${new Date(assignment.due_at).toLocaleString()}` : "No due date";
};

export default function AssignedTrainingPage() {
  const router = useRouter();
  const [assignments, setAssignments] = useState<TrainingAssignment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [startingId, setStartingId] = useState<string | null>(null);

  const load = async () => {
    try {
      setIsLoading(true);
      setAssignments(await trainingRunApi.listMyAssignments());
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not load assigned training.");
    } finally {
      setIsLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  const start = async (assignmentId: string) => {
    try {
      setStartingId(assignmentId);
      const session = await trainingRunApi.startAssignment(assignmentId);
      saveParticipantToken(session.session_id, session.participant_token);
      await router.push(session.redirect_url);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not start training.");
    } finally {
      setStartingId(null);
    }
  };

  return <RequireAuth title="Assigned training" description="Sign in to complete your assigned training."><div className="flex min-h-screen flex-col bg-paper text-ink"><NavBar /><main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}><header className="border-b-2 border-divider pb-[28px]"><Kicker>Your training</Kicker><div className="flex flex-wrap items-end justify-between gap-[16px]"><div><h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">Assigned to you</h1><p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">Training assigned to your verified email. Complete it at your pace before the run closes.</p></div><button type="button" onClick={() => void load()} className={BTN_GHOST}>Refresh</button></div></header>{isLoading ? <div className="flex min-h-[40vh] items-center justify-center"><div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-brand" /></div> : <section className="pt-[36px]" aria-label="Assigned training list"><div className="grid gap-[12px]">{assignments.length ? assignments.map((assignment) => <article key={assignment.id} className="flex flex-wrap items-center justify-between gap-[20px] border-2 border-divider bg-paper p-[20px]"><div><p className="text-[12px] font-extrabold uppercase tracking-[0.14em] text-brand">{assignment.kind === "compliance" ? "Compliance" : "Training"}</p><h2 className="mt-[8px] text-[18px] font-extrabold">{assignment.title}</h2><p className="mt-[5px] text-[14px] text-ink/70">{stateLabel(assignment)} · {assignment.attempts_used}/{assignment.max_attempts ?? "∞"} attempts used</p></div>{assignment.can_retry ? <button type="button" disabled={startingId === assignment.id} onClick={() => void start(assignment.id)} className={`${BTN_PRIMARY} disabled:opacity-50`}>{startingId === assignment.id ? "Starting..." : assignment.attempts_used ? "Retry training" : "Start training"}</button> : <span className="text-[14px] font-extrabold text-ink/60">{assignment.status === "completed" ? "Completed" : "Unavailable"}</span>}</article>) : <p className="border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">You have no training assigned to this verified email.</p>}</div></section>}</main><Footer /></div></RequireAuth>;
}
