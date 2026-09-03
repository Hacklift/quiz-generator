"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { trainingRunApi, type TrainingRunDetail } from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, CONTAINER, Kicker } from "@shared/ui/quizwerk";

const displayDate = (value?: string | null) => value ? new Date(value).toLocaleString() : "-";
const completionLabel = (run: TrainingRunDetail) =>
  run.assigned_count
    ? `${run.completed_count}/${run.assigned_count} recipients`
    : `${run.completed_count} completed`;

export default function TrainingRunDetailPage({ runId }: { runId: string }) {
  const router = useRouter();
  const [run, setRun] = useState<TrainingRunDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isClosing, setIsClosing] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const load = useCallback(async () => {
    try {
      setIsLoading(true);
      setRun(await trainingRunApi.getRun(runId));
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not load training run.");
      await router.replace("/training-runs");
    } finally {
      setIsLoading(false);
    }
  }, [router, runId]);

  useEffect(() => { void load(); }, [load]);

  const closeRun = async () => {
    try {
      setIsClosing(true);
      await trainingRunApi.closeRun(runId);
      setShowCloseConfirm(false);
      toast.success("Training run closed. Its completion register is now fixed.");
      await load();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not close training run.");
    } finally {
      setIsClosing(false);
    }
  };

  const copyLink = async () => {
    if (!run?.access_url) return;
    try {
      await navigator.clipboard.writeText(run.access_url);
      toast.success("Share link copied.");
    } catch {
      toast.error("Could not copy the share link.");
    }
  };

  return (
    <RequireAuth title="Training run" description="Sign in to view training completion.">
      <div className="flex min-h-screen flex-col bg-paper text-ink">
        <NavBar />
        <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
          {isLoading || !run ? <div className="flex min-h-[40vh] items-center justify-center"><div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-brand" /></div> : <>
            <header className="border-b-2 border-divider pb-[28px]">
              <Kicker>{run.kind === "compliance" ? "Compliance register" : "Training completion"}</Kicker>
              <div className="flex flex-wrap items-end justify-between gap-[16px]"><div><h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">{run.title}</h1><p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">{run.status === "closed" ? `Closed ${displayDate(run.closed_at)}. This completion register is retained as the final record.` : `Open until ${displayDate(run.closes_at)}.`}</p></div><div className="flex flex-wrap gap-[12px]"><button type="button" onClick={() => router.push("/training-runs")} className={BTN_GHOST}>All runs</button>{run.status === "open" && <button type="button" disabled={isClosing} onClick={() => setShowCloseConfirm(true)} className={`${BTN_PRIMARY} disabled:opacity-50`}>Close run</button>}</div></div>
            </header>
            <div className="grid gap-[36px] pt-[36px] lg:grid-cols-[minmax(0,1fr)_300px]">
              <section aria-labelledby="register-heading"><Kicker>Per-run register</Kicker><h2 id="register-heading" className="text-[20px] font-extrabold">Completion by person</h2><div className="mt-[20px] overflow-x-auto border-2 border-divider"><table className="min-w-full divide-y-2 divide-divider text-left text-[13px]"><thead className="bg-ink text-paper"><tr><th className="px-[14px] py-[12px]">Recipient</th><th className="px-[14px] py-[12px]">State</th><th className="px-[14px] py-[12px]">Submitted</th><th className="px-[14px] py-[12px]">Score</th><th className="px-[14px] py-[12px]">Attempts</th></tr></thead><tbody className="divide-y divide-divider">{run.completion_register.map((row) => <tr key={row.assignment_id}><td className="px-[14px] py-[12px] font-semibold">{row.recipient_email || row.recipient_name || "Shared-link participant"}</td><td className="px-[14px] py-[12px]">{row.status.replace("_", " ")}</td><td className="px-[14px] py-[12px]">{displayDate(row.completed_at)}</td><td className="px-[14px] py-[12px]">{row.latest_percentage != null ? `${row.latest_percentage}%` : "-"}</td><td className="px-[14px] py-[12px]">{row.attempts_used}/{row.max_attempts ?? "∞"}</td></tr>)}{!run.completion_register.length && <tr><td className="px-[14px] py-[20px] text-ink/70" colSpan={5}>No participants have started this run.</td></tr>}</tbody></table></div></section>
              <aside className="border-2 border-divider bg-paper p-[20px]"><Kicker>Run details</Kicker><dl className="mt-[16px] grid gap-[14px] text-[14px]"><div><dt className="font-extrabold">Completion</dt><dd className="mt-[3px] text-ink/70">{completionLabel(run)}</dd></div><div><dt className="font-extrabold">Duration</dt><dd className="mt-[3px] text-ink/70">{run.time_limit_minutes} minutes</dd></div><div><dt className="font-extrabold">Average score</dt><dd className="mt-[3px] text-ink/70">{run.average_score ?? "-"}</dd></div><div><dt className="font-extrabold">Due date</dt><dd className="mt-[3px] text-ink/70">{displayDate(run.due_at)}</dd></div><div><dt className="font-extrabold">Access</dt><dd className="mt-[3px] text-ink/70">{run.access_mode === "public" ? "Shareable live link" : "Assigned recipients only"}</dd></div></dl>{run.access_mode === "public" && <button type="button" onClick={() => void copyLink()} className={`${BTN_GHOST} mt-[20px] w-full`}>Copy share link</button>}</aside>
            </div>
            {showCloseConfirm && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/55 p-[20px]" role="presentation" onClick={() => !isClosing && setShowCloseConfirm(false)}><section role="dialog" aria-modal="true" aria-labelledby="close-run-title" className="w-full max-w-[520px] border-2 border-ink bg-paper p-[28px] shadow-2xl" onClick={(event) => event.stopPropagation()}><Kicker>Irreversible action</Kicker><h2 id="close-run-title" className="mt-[8px] text-[24px] font-extrabold">Close this training run?</h2><p className="mt-[14px] text-[15px] leading-[25px] text-ink/75">Closing stops new starts and submissions. Any participant currently taking the quiz will be unable to submit, and that attempt will not be counted as completed. The completion register becomes the final retained record and cannot be reopened.</p><p className="mt-[12px] border-l-4 border-brand pl-[12px] text-[14px] font-bold">{run.completion_register.filter((row) => row.status !== "completed").length} participant{run.completion_register.filter((row) => row.status !== "completed").length === 1 ? " is" : "s are"} not completed.</p><div className="mt-[24px] flex flex-wrap justify-end gap-[12px]"><button type="button" disabled={isClosing} onClick={() => setShowCloseConfirm(false)} className={BTN_GHOST}>Cancel</button><button type="button" disabled={isClosing} onClick={() => void closeRun()} className={`${BTN_PRIMARY} disabled:opacity-50`}>{isClosing ? "Closing..." : "Close run permanently"}</button></div></section></div>}
          </>}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
