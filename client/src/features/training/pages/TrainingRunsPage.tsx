"use client";
import { useTranslation } from "react-i18next";

import React, {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
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
import {
  clearTrainingRunIdempotencyKey,
  idempotencyKeyForTrainingRun,
} from "@features/training/lib/trainingRunIdempotency";
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
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const [kind, setKind] = useState<TrainingKind>("business");
  const [purpose, setPurpose] = useState<TrainingPurpose>("onboarding");
  const [quizzes, setQuizzes] = useState<OwnedQuiz[]>([]);
  const [runs, setRuns] = useState<TrainingRunSummary[]>([]);
  const [quizId, setQuizId] = useState("");
  const [recipients, setRecipients] = useState("");
  const [accessMode, setAccessMode] =
    useState<TrainingAccessMode>("assigned_only");
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
      toast.error(uiText("m287f2b7712b68255"));
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
      toast.error(uiText("m8082eb37012f168d"));
      return;
    }
    const recipientEmails = recipients
      .split(/[\s,;]+/)
      .map((email) => email.trim())
      .filter(Boolean);
    if (accessMode === "assigned_only" && !recipientEmails.length) {
      toast.error(uiText("ma7075e148ccf4f0f"));
      return;
    }
    const closesAtDate = new Date(closesAt);
    const dueAtDate = dueAt ? new Date(dueAt) : null;
    if (Number.isNaN(closesAtDate.getTime())) {
      toast.error(uiText("m95d8ad99a45937fb"));
      return;
    }
    if (closesAtDate.getTime() <= Date.now() + timeLimitMinutes * 60_000) {
      toast.error(uiText("m7e120f69077f8c88"));
      return;
    }
    if (dueAtDate && dueAtDate.getTime() > closesAtDate.getTime()) {
      toast.error(uiText("m69d1368aad5a3fac"));
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
      // A confirmed response completes this create intent. A subsequent,
      // deliberate submission with the same fields must create a new run.
      clearTrainingRunIdempotencyKey(pendingCreateKeys.current, payload);
      toast.success(uiText("ma461617c75db7511"));
      await router.push(ROUTES.trainingRun(run.id));
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not create training run.",
      );
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <NavBar />
      <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
        <header className="border-b-2 border-divider pb-[28px]">
          <Kicker>
            {kind === uiText("m29a3e14798aa2363")
              ? uiText("m4a109cc49467be33")
              : uiText("m76f68a75f01ed76f")}{" "}
            {uiText("mc2fb788c7deedbea")}
          </Kicker>
          <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
            {uiText("m78ae22e506dc5fd2")}
          </h1>
          <p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
            {uiText("m70a70d1494527dbe")}
          </p>
        </header>

        <div className="grid gap-[36px] pt-[36px] lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)]">
          <section aria-labelledby="runs-heading">
            <div className="flex items-end justify-between gap-[16px] border-t-2 border-divider pt-[28px]">
              <div>
                <Kicker>{uiText("m3a0d288f5098acdd")}</Kicker>
                <h2 id="runs-heading" className="text-[20px] font-extrabold">
                  {uiText("mc37d503d7e076565")}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => void load()}
                className={BTN_GHOST}
              >
                {uiText("m0e91610117029a62")}
              </button>
            </div>
            <div className="mt-[20px] grid gap-[12px]">
              {isLoading ? (
                <p className="border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
                  {uiText("md11ca191e75a7f25")}
                </p>
              ) : loadError ? (
                <p
                  role="alert"
                  className="border-2 border-brand bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70"
                >
                  {uiText("m9c634e1923f29a88")}
                </p>
              ) : runs.length ? (
                runs.map((run) => (
                  <button
                    key={run.id}
                    type="button"
                    onClick={() => router.push(ROUTES.trainingRun(run.id))}
                    className="grid w-full grid-cols-1 gap-[10px] border-2 border-divider bg-paper p-[16px] text-left transition hover:border-ink/60 sm:grid-cols-[minmax(0,1fr)_auto]"
                  >
                    <span>
                      <strong className="block">{run.title}</strong>
                      <span className="mt-[3px] block text-[13px] text-ink/65">
                        {run.kind === uiText("m29a3e14798aa2363")
                          ? uiText("m4a109cc49467be33")
                          : uiText("m76f68a75f01ed76f")}{" "}
                        ·{" "}
                        {run.status === uiText("mc3eefb58d7c42440")
                          ? uiText("mc21ead0614e7e1b7")
                          : `Closes ${new Date(run.closes_at).toLocaleDateString()}`}
                      </span>
                    </span>
                    <span className="text-[13px] font-extrabold">
                      {completionLabel(run)}
                    </span>
                  </button>
                ))
              ) : (
                <p className="border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70">
                  {uiText("mcb8b55daea56b2d4")}
                </p>
              )}
            </div>
          </section>

          <section
            className="border-2 border-divider bg-paper p-[20px]"
            aria-labelledby="create-run-heading"
          >
            <Kicker>{uiText("mdcb34ce2197c6af8")}</Kicker>
            <h2 id="create-run-heading" className="text-[20px] font-extrabold">
              {uiText("m2a359f5ecc2b5b04")}
            </h2>
            <form className="mt-[20px] space-y-[16px]" onSubmit={createRun}>
              <label className="block text-[13px] font-extrabold">
                {uiText("ma923004860834bdd")}
                <select
                  value={kind}
                  onChange={(event) =>
                    setKind(event.target.value as TrainingKind)
                  }
                  className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                >
                  <option value="business">
                    {uiText("m0576e07036bd5513")}
                  </option>
                  <option value="compliance">
                    {uiText("m0e0a5103bb78a732")}
                  </option>
                </select>
              </label>
              <label className="block text-[13px] font-extrabold">
                {uiText("md4e8830a71c73edf")}
                <select
                  value={purpose}
                  onChange={(event) =>
                    setPurpose(event.target.value as TrainingPurpose)
                  }
                  className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                >
                  {PURPOSES[kind].map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-[13px] font-extrabold">
                {uiText("m03aa7dc16797a82b")}
                <select
                  value={quizId}
                  onChange={(event) => setQuizId(event.target.value)}
                  className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                >
                  <option value="">{uiText("mf3dcbc36d20431b8")}</option>
                  {quizzes.map((quiz) => (
                    <option key={quiz.id} value={quiz.id}>
                      {quiz.title}
                    </option>
                  ))}
                </select>
              </label>
              {!quizzes.length && (
                <p className="text-[13px] leading-[20px] text-ink/70">
                  {uiText("m3d2ae0179a550ae2")}
                  <button
                    type="button"
                    className="font-extrabold underline"
                    onClick={() => router.push("/generate")}
                  >
                    {uiText("me1963ec5df847781")}
                  </button>
                </p>
              )}
              <label className="block text-[13px] font-extrabold">
                {uiText("mec5ba0abb717da87")}
                <select
                  value={accessMode}
                  disabled={kind === "compliance"}
                  onChange={(event) => {
                    const nextMode = event.target.value as TrainingAccessMode;
                    setAccessMode(nextMode);
                    if (nextMode === "public") {
                      setRecipients("");
                      setSendEmails(false);
                    }
                  }}
                  className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium disabled:cursor-not-allowed disabled:bg-divider"
                >
                  <option value="assigned_only">
                    {uiText("m6d31fe05362dec7d")}
                  </option>
                  {kind === uiText("m11d40417959631d3") && (
                    <option value="public">
                      {uiText("m8e99b2dff44ebdd4")}
                    </option>
                  )}
                </select>
              </label>
              {kind === uiText("m29a3e14798aa2363") && (
                <p className="-mt-[10px] text-[12px] leading-[18px] text-ink/65">
                  {uiText("m718ba9d6d369086b")}
                </p>
              )}
              {accessMode === uiText("m990770a023d0c0e4") ? (
                <>
                  <label className="block text-[13px] font-extrabold">
                    {uiText("m1e8568a82c2620ce")}
                    <input
                      value={recipients}
                      onChange={(event) => setRecipients(event.target.value)}
                      placeholder={uiText("m603a789446e0a8d2")}
                      className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                    />
                  </label>
                  <p className="-mt-[10px] text-[12px] leading-[18px] text-ink/65">
                    {uiText("m987223b5c9c9e0c9")}
                  </p>
                </>
              ) : (
                <p className="text-[12px] leading-[18px] text-ink/65">
                  {uiText("m52a96e3ca65bbbd8")}
                </p>
              )}
              <div className="grid gap-[16px] sm:grid-cols-2">
                <label className="block text-[13px] font-extrabold">
                  {uiText("me1cb6d30fa3f17ee")}
                  <input
                    type="datetime-local"
                    value={dueAt}
                    onChange={(event) => setDueAt(event.target.value)}
                    className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                  />
                </label>
                <label className="block text-[13px] font-extrabold">
                  {uiText("m74d2ed725be16273")}
                  <input
                    type="datetime-local"
                    value={closesAt}
                    onChange={(event) => setClosesAt(event.target.value)}
                    className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                  />
                </label>
              </div>
              <label className="block text-[13px] font-extrabold">
                {uiText("mf6bdf76fe5aee0fa")}
                <select
                  value={timeLimitMinutes}
                  onChange={(event) =>
                    setTimeLimitMinutes(Number(event.target.value))
                  }
                  className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                >
                  {DURATIONS.map((minutes) => (
                    <option key={minutes} value={minutes}>
                      {minutes} {uiText("m90e63d85fa1ab2c8")}
                    </option>
                  ))}
                </select>
              </label>
              <p className="-mt-[10px] text-[12px] leading-[18px] text-ink/65">
                {uiText("mc8c4f01c06128eef")}
              </p>
              <label className="block text-[13px] font-extrabold">
                {uiText("m06e70139fcf5e5c7")}
                <select
                  value={maxAttempts}
                  onChange={(event) => setMaxAttempts(event.target.value)}
                  className="mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium"
                >
                  <option value="1">{uiText("m29b39c391ab74f0d")}</option>
                  <option value="2">{uiText("m8954a071c10dc478")}</option>
                  <option value="unlimited">
                    {uiText("ma6d83b6baec44842")}
                  </option>
                </select>
              </label>
              {accessMode === uiText("m990770a023d0c0e4") && (
                <label className="flex items-start gap-[10px] text-[13px] leading-[20px]">
                  <input
                    type="checkbox"
                    checked={sendEmails}
                    onChange={(event) => setSendEmails(event.target.checked)}
                    className="mt-[3px] h-[16px] w-[16px]"
                  />
                  {uiText("m74b39ee8d11c1c10")}
                </label>
              )}
              <button
                type="submit"
                disabled={isCreating || !quizId}
                className={`${BTN_PRIMARY} w-full disabled:cursor-not-allowed disabled:opacity-50`}
              >
                {isCreating
                  ? uiText("ma8e9b9789b4ae9e2")
                  : uiText("mad78ff58410183e1")}
              </button>
            </form>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
