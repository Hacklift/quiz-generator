"use client";

import React, { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireTrainingManager from "@features/training/components/RequireTrainingManager";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import {
  trainingRunApi,
  type CreateTrainingRunPayload,
  type OwnedQuiz,
  type TrainingAccessMode,
  type TrainingKind,
  type TrainingPurpose,
  type TrainingRunSummary,
} from "@features/training/api/trainingRunApi";
import { idempotencyKeyForTrainingRun } from "@features/training/lib/trainingRunIdempotency";
import { BTN_GHOST, BTN_PRIMARY, CONTAINER, Kicker } from "@shared/ui/quizwerk";
import { ROUTES } from "@shared/config/patterns/routes";

const localDateTime = (daysFromNow: number) => {
  const date = new Date(Date.now() + daysFromNow * 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};

const PURPOSES: Record<TrainingKind, Array<[TrainingPurpose, string]>> = {
  business: [
    ["onboarding", "Employee onboarding"],
    ["product_knowledge", "Product knowledge"],
    ["custom", "Custom training"],
  ],
  compliance: [
    ["harassment_prevention", "Harassment prevention"],
    ["health_and_safety", "Health & safety"],
    ["custom", "Custom compliance training"],
  ],
};

const DURATIONS = [5, 10, 15, 20, 30, 45, 60, 90, 120];

const completionLabel = (run: TrainingRunSummary) =>
  run.assigned_count
    ? `${run.completed_count}/${run.assigned_count} complete`
    : `${run.completed_count} completed`;

export default function TrainingRunsPage() {
  return (
    <RequireTrainingManager>
      <TrainingRunsContent />
    </RequireTrainingManager>
  );
}

function TrainingRunsContent() {
  const router = useRouter();
  const [kind, setKind] = useState<TrainingKind>("business");
  const [purpose, setPurpose] = useState<TrainingPurpose>("onboarding");
  const [quizzes, setQuizzes] = useState<OwnedQuiz[]>([]);
  const [runs, setRuns] = useState<TrainingRunSummary[]>([]);
  const [quizId, setQuizId] = useState("");
  const [recipients, setRecipients] = useState("");
  const [accessMode, setAccessMode] = useState<TrainingAccessMode>("assigned_only");
  const [timeLimitMinutes, setTimeLimitMinutes] = useState(20);
  const [dueAt, setDueAt] = useState(localDateTime(7));
  const [closesAt, setClosesAt] = useState(localDateTime(14));
  const [maxAttempts, setMaxAttempts] = useState("1");
  const [sendEmails, setSendEmails] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const pendingCreateKeys = useRef(new Map<string, string>());

  const load = useCallback(async () => {
    try {
      setIsLoading(true);
      const [ownedQuizzes, ownerRuns] = await Promise.all([
        trainingRunApi.listOwnedQuizzes(),
        trainingRunApi.listRuns(),
      ]);
      setQuizzes(ownedQuizzes);
      setRuns(ownerRuns);
      setLoadError(false);
    } catch {
      setLoadError(true);
      toast.error("Could not load training runs.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (router.isReady) {
      setKind(router.query.kind === "compliance" ? "compliance" : "business");
    }
  }, [router.isReady, router.query.kind]);

  useEffect(() => {
    setPurpose(kind === "compliance" ? "harassment_prevention" : "onboarding");
    if (kind === "compliance") setAccessMode("assigned_only");
  }, [kind]);

  const createRun = async (event: FormEvent) => {
    event.preventDefault();
    if (!quizId) {
      toast.error("Generate a quiz before creating a training run.");
      return;
    }
    const recipientEmails = recipients.split(/[\s,;]+/).map((email) => email.trim()).filter(Boolean);
    if (accessMode === "assigned_only" && !recipientEmails.length) {
      toast.error("Add at least one recipient for assigned training.");
      return;
    }
    const closesAtDate = new Date(closesAt);
    const dueAtDate = dueAt ? new Date(dueAt) : null;
    if (Number.isNaN(closesAtDate.getTime())) {
      toast.error("Choose a valid run close time.");
      return;
    }
    if (closesAtDate.getTime() <= Date.now() + timeLimitMinutes * 60_000) {
      toast.error("The run close time must allow one full quiz duration.");
      return;
    }
    if (dueAtDate && dueAtDate.getTime() > closesAtDate.getTime()) {
      toast.error("The due date cannot be after the run closes.");
      return;
    }
    try {
      setIsCreating(true);
      const payload: CreateTrainingRunPayload = {
        quiz_id: quizId,
        kind,
        purpose,
        time_limit_minutes: timeLimitMinutes,
        closes_at: closesAtDate.toISOString(),
        due_at: dueAtDate?.toISOString(),
        access_mode: accessMode,
        recipient_emails: recipientEmails,
        max_attempts: maxAttempts === "unlimited" ? null : Number(maxAttempts),
        send_email_invitations: sendEmails && recipientEmails.length > 0,
      };
      const idempotencyKey = idempotencyKeyForTrainingRun(
        pendingCreateKeys.current,
        payload,
        () => crypto.randomUUID(),
      );
      const run = await trainingRunApi.createRun(payload, idempotencyKey);
      toast.success("Training run created.");
      await router.push(ROUTES.trainingRun(run.id));
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not create training run.");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
        <NavBar />
        <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
          <header className="border-b-2 border-divider pb-[28px]">
            <Kicker>{kind === "compliance" ? "Compliance" : "Business"} training</Kicker>
            <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">Create and measure a training run</h1>
            <p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">A run is one delivery event for a reusable quiz. Assign it to people, set a due date, then review one completion register.</p>
          </header>

          <div className="grid gap-[36px] pt-[36px] lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)]">
            <section aria-labelledby="runs-heading">
              <div className="flex items-end justify-between gap-[16px] border-t-2 border-divider pt-[28px]">
                <div><Kicker>Existing runs</Kicker><h2 id="runs-heading" className="text-[20px] font-extrabold">Open and closed training</h2></div>
                <button type="button" onClick={() => void load()} className={BTN_GHOST}>Refresh</button>
              </div>
              <div className="mt-[20px] grid gap-[12px]">
                {isLoading ? <p className="border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">Loading training runs...</p> : loadError ? <p role="alert" className="border-2 border-brand bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">Training runs could not be loaded. Refresh to try again.</p> : runs.length ? runs.map((run) => (
                  <button key={run.id} type="button" onClick={() => router.push(ROUTES.trainingRun(run.id))} className="grid w-full grid-cols-1 gap-[10px] border-2 border-divider bg-paper p-[16px] text-left transition hover:border-ink/60 sm:grid-cols-[minmax(0,1fr)_auto]">
                    <span><strong className="block">{run.title}</strong><span className="mt-[3px] block text-[13px] text-ink/65">{run.kind === "compliance" ? "Compliance" : "Business"} · {run.status === "closed" ? "Closed" : `Closes ${new Date(run.closes_at).toLocaleDateString()}`}</span></span>
                    <span className="text-[13px] font-extrabold">{completionLabel(run)}</span>
                  </button>
                )) : <p className="border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">No runs yet. Start by choosing one of your generated quizzes.</p>}
              </div>
            </section>

            <section className="border-2 border-divider bg-paper p-[20px]" aria-labelledby="create-run-heading">
              <Kicker>New run</Kicker>
              <h2 id="create-run-heading" className="text-[20px] font-extrabold">Distribute a quiz</h2>
              <form className="mt-[20px] space-y-[16px]" onSubmit={createRun}>
                <label className="block text-[13px] font-extrabold">Training type<select value={kind} onChange={(event) => setKind(event.target.value as TrainingKind)} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"><option value="business">Business training</option><option value="compliance">Compliance training</option></select></label>
                <label className="block text-[13px] font-extrabold">Purpose<select value={purpose} onChange={(event) => setPurpose(event.target.value as TrainingPurpose)} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium">{PURPOSES[kind].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                <label className="block text-[13px] font-extrabold">Quiz<select value={quizId} onChange={(event) => setQuizId(event.target.value)} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"><option value="">Choose a generated quiz</option>{quizzes.map((quiz) => <option key={quiz.id} value={quiz.id}>{quiz.title}</option>)}</select></label>
                {!quizzes.length && <p className="text-[13px] leading-[20px] text-ink/70">No owned quizzes are available. <button type="button" className="font-extrabold underline" onClick={() => router.push("/generate")}>Generate one first.</button></p>}
                <label className="block text-[13px] font-extrabold">Access<select value={accessMode} disabled={kind === "compliance"} onChange={(event) => { const nextMode = event.target.value as TrainingAccessMode; setAccessMode(nextMode); if (nextMode === "public") { setRecipients(""); setSendEmails(false); } }} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium disabled:cursor-not-allowed disabled:bg-divider"><option value="assigned_only">Assigned recipients only</option>{kind === "business" && <option value="public">Shareable live link</option>}</select></label>
                {kind === "compliance" && <p className="-mt-[10px] text-[12px] leading-[18px] text-ink/65">Compliance runs are assigned-only so every completion is linked to a verified recipient.</p>}
                {accessMode === "assigned_only" ? <><label className="block text-[13px] font-extrabold">Recipients<input value={recipients} onChange={(event) => setRecipients(event.target.value)} placeholder="name@example.com, team@example.com" className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium" /></label><p className="-mt-[10px] text-[12px] leading-[18px] text-ink/65">Required. Separate addresses with commas, spaces, or new lines. Recipients sign in with this verified email to access the training.</p></> : <p className="text-[12px] leading-[18px] text-ink/65">Anyone with the link can take this training. Their name and optional email are self-reported in the completion register.</p>}
                <div className="grid gap-[16px] sm:grid-cols-2"><label className="block text-[13px] font-extrabold">Due date<input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium" /></label><label className="block text-[13px] font-extrabold">Run closes<input type="datetime-local" value={closesAt} onChange={(event) => setClosesAt(event.target.value)} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium" /></label></div>
                <label className="block text-[13px] font-extrabold">Quiz duration<select value={timeLimitMinutes} onChange={(event) => setTimeLimitMinutes(Number(event.target.value))} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium">{DURATIONS.map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}</select></label>
                <p className="-mt-[10px] text-[12px] leading-[18px] text-ink/65">Participants can only start when enough time remains to finish before the run closes.</p>
                <label className="block text-[13px] font-extrabold">Attempts<select value={maxAttempts} onChange={(event) => setMaxAttempts(event.target.value)} className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"><option value="1">One attempt</option><option value="2">Two attempts</option><option value="unlimited">Unlimited attempts</option></select></label>
                {accessMode === "assigned_only" && <label className="flex items-start gap-[10px] text-[13px] leading-[20px]"><input type="checkbox" checked={sendEmails} onChange={(event) => setSendEmails(event.target.checked)} className="mt-[3px] h-[16px] w-[16px]" />Email assignment invitations to recipients.</label>}
                <button type="submit" disabled={isCreating || !quizId} className={`${BTN_PRIMARY} w-full disabled:cursor-not-allowed disabled:opacity-50`}>{isCreating ? "Creating run..." : "Create training run"}</button>
              </form>
            </section>
          </div>
        </main>
        <Footer />
    </div>
  );
}
