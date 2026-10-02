import React, {
  FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import {
  LiveQuizSummary,
  liveQuizService,
  type LiveResultsExportFormat,
} from "@features/live-quiz/api/liveQuizService";
import { downloadLiveResults } from "@features/live-quiz/lib/downloadLiveResults";
import { ROUTES } from "@shared/config/patterns/routes";
import {
  archivo,
  BTN_GHOST,
  BTN_PRIMARY,
  CONTAINER,
  Kicker,
} from "@shared/ui/quizwerk";

const formatDateTime = (isoString: string | null | undefined): string => {
  if (!isoString) return "-";
  try {
    return new Date(isoString).toLocaleString();
  } catch {
    return "-";
  }
};

const tomorrowLocalValue = () => {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};

// Mirrors the server's join check: a code without an expiry is rejected
// ("Access code has expired"), so it is treated as unusable here too.
const isExpired = (expiresAt: string | null | undefined) =>
  !expiresAt || new Date(expiresAt).getTime() <= Date.now();

const MAX_DURATION_MINUTES = 1440;

type AccessCodeFormError = {
  field: "duration" | "expiresAt";
  message: string;
};

/** Returns the first invalid field and a user-facing message, if any. */
const validateAccessCodeForm = (
  durationInput: string,
  expiresAtInput: string,
): AccessCodeFormError | null => {
  const minutes = Number(durationInput);
  if (
    durationInput.trim() === "" ||
    !Number.isInteger(minutes) ||
    minutes < 1 ||
    minutes > MAX_DURATION_MINUTES
  ) {
    return {
      field: "duration",
      message: `Enter a duration between 1 and ${MAX_DURATION_MINUTES} whole minutes.`,
    };
  }
  const expiry = new Date(expiresAtInput).getTime();
  if (!expiresAtInput || Number.isNaN(expiry)) {
    return {
      field: "expiresAt",
      message: "Choose when the access code expires.",
    };
  }
  if (expiry <= Date.now()) {
    return {
      field: "expiresAt",
      message: "Choose an expiry time in the future.",
    };
  }
  return null;
};

const FOCUSABLE =
  'button:not([disabled]), input:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])';

const statusLabel: Record<string, string> = {
  active: "Active",
  in_progress: "In Progress",
  completed: "Completed",
  expired: "Expired",
};

const CHIP =
  "inline-flex items-center gap-[6px] border-2 px-[8px] py-[2px] text-[11px] font-extrabold uppercase tracking-[0.08em]";

const statusClass: Record<string, string> = {
  active: "border-brand bg-brand text-paper",
  in_progress: "border-brand text-brand",
  completed: "border-ink/20 bg-ink/[0.06] text-ink/75",
  expired: "border-red-700 text-red-700",
};

const FIELD =
  "mt-[6px] block w-full border-2 border-ink bg-paper px-[12px] py-[10px] font-medium outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand";

/** Slightly smaller buttons below 640px so action rows fit a 320px screen. */
const BTN_COMPACT =
  "max-sm:min-h-[40px] max-sm:px-[12px] max-sm:text-[13px]";

const STAT_LABEL =
  "whitespace-nowrap text-[10px] font-extrabold uppercase tracking-[0.04em] text-ink/60 sm:text-[11px] sm:tracking-[0.1em]";

const PANEL =
  "border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70";

export const MyLiveQuizzesPage: React.FC = () => {
  const router = useRouter();
  const [quizzes, setQuizzes] = useState<LiveQuizSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [quizToGenerateFor, setQuizToGenerateFor] =
    useState<LiveQuizSummary | null>(null);
  const [duration, setDuration] = useState("20");
  const [formError, setFormError] = useState<AccessCodeFormError | null>(
    null,
  );
  const [expiresAt, setExpiresAt] = useState(tomorrowLocalValue());
  const [isGenerating, setIsGenerating] = useState(false);
  const [exportingQuizId, setExportingQuizId] = useState<string | null>(null);
  const [openActionsQuizId, setOpenActionsQuizId] = useState<string | null>(
    null,
  );
  const actionsMenuRef = useRef<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLFormElement | null>(null);
  const durationInputRef = useRef<HTMLInputElement | null>(null);
  const dialogTriggerRef = useRef<HTMLElement | null>(null);

  const loadLiveQuizzes = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await liveQuizService.listLiveQuizzes();
      setQuizzes(data);
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not load live quizzes.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLiveQuizzes();
  }, [loadLiveQuizzes]);

  // Close the export menu on an outside click or Escape.
  useEffect(() => {
    if (!openActionsQuizId) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (!actionsMenuRef.current?.contains(event.target as Node)) {
        setOpenActionsQuizId(null);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      actionsMenuRef.current
        ?.querySelector<HTMLButtonElement>("button[aria-expanded]")
        ?.focus();
      setOpenActionsQuizId(null);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openActionsQuizId]);

  const openGenerationDialog = (quiz: LiveQuizSummary) => {
    dialogTriggerRef.current = document.activeElement as HTMLElement | null;
    setQuizToGenerateFor(quiz);
    setDuration(String(quiz.time_limit_minutes || 20));
    setExpiresAt(tomorrowLocalValue());
    setFormError(null);
  };

  const closeGenerationDialog = useCallback(() => {
    if (isGenerating) return;
    setQuizToGenerateFor(null);
    setFormError(null);
    dialogTriggerRef.current?.focus();
  }, [isGenerating]);

  const isDialogOpen = quizToGenerateFor !== null;

  useEffect(() => {
    if (!isDialogOpen) return;
    durationInputRef.current?.focus();
  }, [isDialogOpen]);

  useEffect(() => {
    if (!isDialogOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeGenerationDialog();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isDialogOpen, closeGenerationDialog]);

  // Keep Tab / Shift+Tab inside the dialog while it is open.
  const trapDialogFocus = (event: React.KeyboardEvent<HTMLFormElement>) => {
    if (event.key !== "Tab" || !dialogRef.current) return;
    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const generateAccessCode = async (event: FormEvent) => {
    event.preventDefault();
    if (!quizToGenerateFor) return;

    const validationError = validateAccessCodeForm(duration, expiresAt);
    if (validationError) {
      setFormError(validationError);
      return;
    }
    setFormError(null);

    try {
      setIsGenerating(true);
      const response = await liveQuizService.createAccessCode({
        quizId: quizToGenerateFor.quiz_id,
        time_limit_minutes: Number(duration),
        access_code_expires_at: new Date(expiresAt).toISOString(),
        participant_access_mode:
          quizToGenerateFor.participant_access_mode || "public",
        invited_emails: quizToGenerateFor.invited_emails || [],
      });
      setQuizToGenerateFor(null);
      dialogTriggerRef.current = null;
      await loadLiveQuizzes();
      toast.success(`Access code ${response.access_code} generated.`);
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not generate access code.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const exportResults = async (
    quiz: LiveQuizSummary,
    format: LiveResultsExportFormat,
  ) => {
    setOpenActionsQuizId(null);
    setExportingQuizId(quiz.quiz_id);
    const toastId = toast.loading("Preparing results export...");
    try {
      await downloadLiveResults(
        quiz.quiz_id,
        format,
        `${quiz.title || "live-quiz"}-results`,
      );
      toast.success("Session results downloaded.", { id: toastId });
    } catch {
      toast.error("Could not export session results.", { id: toastId });
    } finally {
      setExportingQuizId(null);
    }
  };

  const openCodeCount = quizzes.filter(
    (quiz) => quiz.access_code && !isExpired(quiz.access_code_expires_at),
  ).length;
  const participantTotal = quizzes.reduce(
    (total, quiz) => total + (quiz.participant_count || 0),
    0,
  );

  return (
    <RequireAuth
      title="Live Quizzes"
      description="Sign in to manage your live quizzes."
    >
      <div
        className={`${archivo.className} flex min-h-screen flex-col bg-paper text-ink`}
      >
        <NavBar />
        <main className={`${CONTAINER} flex-1 py-[clamp(24px,5vw,56px)]`}>
          <header className="pb-[20px] sm:pb-[28px]">
            <Kicker>Live quizzes</Kicker>
            <div className="flex flex-col gap-[16px] sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
              <div className="min-w-0">
                <h1 className="text-[clamp(26px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
                  Your live sessions
                </h1>
                <p className="mt-[8px] max-w-[58ch] text-[14px] leading-[22px] text-ink/[0.78] sm:mt-[12px] sm:text-[15.5px] sm:leading-[28px]">
                  Generate access codes and watch participants join
                  <span className="hidden sm:inline">
                    , then export results when a session ends
                  </span>
                  .
                </p>
              </div>
              <div className="grid grid-cols-2 gap-[10px] sm:flex sm:gap-[12px]">
                <button
                  type="button"
                  onClick={() => void loadLiveQuizzes()}
                  disabled={isLoading}
                  className={`${BTN_GHOST} ${BTN_COMPACT} disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={() => router.push(ROUTES.GENERATE)}
                  className={`${BTN_PRIMARY} ${BTN_COMPACT}`}
                >
                  Create quiz
                </button>
              </div>
            </div>
          </header>

          {!isLoading && quizzes.length > 0 && (
            <dl className="grid grid-cols-3 gap-[10px] sm:gap-[14px]">
              {[
                ["Quizzes", "Live quizzes", quizzes.length],
                ["Open codes", "Open access codes", openCodeCount],
                ["Joined", "Participants", participantTotal],
              ].map(([short, label, value]) => (
                <div
                  key={label}
                  className="min-w-0 border-t-2 border-divider pt-[10px] sm:pt-[14px]"
                >
                  <dt className="text-[10px] font-extrabold uppercase tracking-[0.06em] text-ink/60 sm:text-[12px] sm:tracking-[0.08em]">
                    <span aria-hidden="true" className="sm:hidden">
                      {short}
                    </span>
                    <span className="max-sm:sr-only">{label}</span>
                  </dt>
                  <dd className="mt-[2px] text-[22px] font-extrabold [font-variant-numeric:tabular-nums] sm:mt-[4px] sm:text-[30px]">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          )}

          <section
            aria-labelledby="sessions-heading"
            className="pt-[28px] sm:pt-[36px]"
          >
            <div className="hidden sm:block">
              <Kicker>All sessions</Kicker>
            </div>
            <h2
              id="sessions-heading"
              className="text-[18px] font-extrabold sm:text-[20px]"
            >
              Quizzes and access codes
            </h2>

            <div className="mt-[14px] sm:mt-[20px]">
              {isLoading ? (
                <p className={PANEL}>Loading live quizzes...</p>
              ) : quizzes.length === 0 ? (
                <div className={PANEL}>
                  <p className="font-extrabold text-ink">No live quizzes yet.</p>
                  <p className="mt-[4px]">
                    Create a quiz and share it live. It will appear here with
                    its access code and participant activity.
                  </p>
                  <button
                    type="button"
                    onClick={() => router.push(ROUTES.GENERATE)}
                    className={`${BTN_PRIMARY} ${BTN_COMPACT} mt-[16px]`}
                  >
                    Create quiz
                  </button>
                </div>
              ) : (
                <ul className="grid gap-[10px] sm:gap-[12px]">
                  {quizzes.map((quiz) => {
                    const codeExpired = isExpired(quiz.access_code_expires_at);
                    const isMenuOpen = openActionsQuizId === quiz.quiz_id;
                    return (
                      <li
                        key={quiz.quiz_id}
                        className="border-2 border-divider bg-paper p-[14px] transition hover:border-ink/60 sm:p-[20px]"
                      >
                        <div className="flex flex-col gap-[14px] md:flex-row md:items-start md:justify-between md:gap-[24px]">
                          <div className="min-w-0">
                            <span
                              className={`${CHIP} ${
                                statusClass[quiz.status] ||
                                "border-ink/20 bg-ink/[0.06] text-ink/75"
                              }`}
                            >
                              {quiz.status === "active" && (
                                <span className="h-[6px] w-[6px] animate-live-pulse bg-paper" />
                              )}
                              {statusLabel[quiz.status] || quiz.status}
                            </span>
                            <h3 className="mt-[8px] break-words text-[16px] font-extrabold leading-[1.3] sm:mt-[10px] sm:text-[18px]">
                              {quiz.title}
                            </h3>
                            <p className="mt-[2px] text-[12px] text-ink/65 sm:mt-[3px] sm:text-[13px]">
                              Created {formatDateTime(quiz.created_at)}
                            </p>
                          </div>

                          <div className="flex flex-wrap gap-[8px] md:shrink-0 md:flex-nowrap">
                            {(!quiz.access_code || codeExpired) && (
                              <button
                                type="button"
                                onClick={() => openGenerationDialog(quiz)}
                                className={`${BTN_PRIMARY} ${BTN_COMPACT} basis-full sm:basis-auto`}
                              >
                                {quiz.access_code
                                  ? "New access code"
                                  : "Generate access code"}
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() =>
                                router.push(ROUTES.myLiveQuiz(quiz.quiz_id))
                              }
                              className={`${BTN_GHOST} ${BTN_COMPACT} flex-1 sm:flex-none`}
                            >
                              View details
                            </button>
                            <div
                              className="relative"
                              ref={isMenuOpen ? actionsMenuRef : undefined}
                            >
                              <button
                                type="button"
                                aria-label={`More actions for ${quiz.title}`}
                                aria-expanded={isMenuOpen}
                                onClick={() =>
                                  setOpenActionsQuizId((current) =>
                                    current === quiz.quiz_id
                                      ? null
                                      : quiz.quiz_id,
                                  )
                                }
                                disabled={exportingQuizId === quiz.quiz_id}
                                className={`${BTN_GHOST} ${BTN_COMPACT} w-[44px] text-[20px] leading-none max-sm:w-[40px] max-sm:text-[18px] disabled:cursor-wait disabled:opacity-50`}
                              >
                                &#8942;
                              </button>
                              {isMenuOpen && (
                                <div className="absolute right-0 z-20 mt-[6px] w-[180px] border-2 border-ink bg-paper py-[8px] text-left">
                                  <p className="px-[14px] pb-[6px] text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
                                    Export results
                                  </p>
                                  {(["csv", "pdf", "txt"] as const).map(
                                    (format) => (
                                      <button
                                        key={format}
                                        type="button"
                                        onClick={() =>
                                          exportResults(quiz, format)
                                        }
                                        className="block w-full px-[14px] py-[8px] text-left text-[14px] font-semibold hover:bg-ink/[0.07] focus-visible:bg-ink/[0.07] focus-visible:outline-none"
                                      >
                                        {format === "txt"
                                          ? "Text"
                                          : format.toUpperCase()}
                                      </button>
                                    ),
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <dl className="mt-[14px] grid grid-cols-3 gap-x-[10px] gap-y-[12px] border-t-2 border-divider pt-[12px] sm:mt-[18px] sm:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))] sm:gap-x-[24px] sm:pt-[16px]">
                          <div className="col-span-3 min-w-0 sm:col-span-1">
                            <dt className={STAT_LABEL}>Access code</dt>
                            {quiz.access_code ? (
                              <dd className="mt-[4px]">
                                <span
                                  className={`block font-mono text-[18px] font-extrabold tracking-[0.12em] sm:text-[20px] ${
                                    codeExpired ? "text-ink/40 line-through" : ""
                                  }`}
                                >
                                  {quiz.access_code}
                                </span>
                                <span
                                  className={`mt-[2px] block text-[12px] ${
                                    codeExpired
                                      ? "font-extrabold text-red-700"
                                      : "text-ink/65"
                                  }`}
                                >
                                  {!quiz.access_code_expires_at
                                    ? "No expiry set"
                                    : `${codeExpired ? "Expired" : "Expires"} ${formatDateTime(quiz.access_code_expires_at)}`}
                                </span>
                              </dd>
                            ) : (
                              <dd className="mt-[4px] text-[14px] text-ink/65">
                                No code yet
                              </dd>
                            )}
                          </div>
                          {[
                            ["Joined", quiz.participant_count],
                            ["Completed", quiz.completed_count],
                            ["Avg score", quiz.average_score ?? "—"],
                          ].map(([label, value]) => (
                            <div key={label} className="min-w-0">
                              <dt className={STAT_LABEL}>{label}</dt>
                              <dd className="mt-[4px] text-[17px] font-extrabold [font-variant-numeric:tabular-nums] sm:text-[20px]">
                                {value}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </section>
        </main>

        {quizToGenerateFor && (
          <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/55 p-[12px] sm:p-[20px]"
            role="presentation"
            onClick={closeGenerationDialog}
          >
            <form
              role="dialog"
              aria-modal="true"
              aria-labelledby="access-code-title"
              ref={dialogRef}
              noValidate
              onSubmit={generateAccessCode}
              onKeyDown={trapDialogFocus}
              onClick={(event) => event.stopPropagation()}
              className="w-full max-w-[480px] border-2 border-ink bg-paper p-[18px] sm:p-[28px]"
            >
              <Kicker>Access code</Kicker>
              <h2
                id="access-code-title"
                className="text-[20px] font-extrabold leading-[1.15] sm:text-[24px]"
              >
                {quizToGenerateFor.access_code
                  ? "Generate a new access code"
                  : "Generate an access code"}
              </h2>
              <p className="mt-[8px] text-[14px] leading-[22px] text-ink/70">
                For &ldquo;{quizToGenerateFor.title}&rdquo;. Participants enter
                this code to join.
              </p>
              <div className="mt-[20px] space-y-[16px]">
                <label className="block text-[13px] font-extrabold">
                  Duration minutes
                  <input
                    ref={durationInputRef}
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={MAX_DURATION_MINUTES}
                    step={1}
                    value={duration}
                    aria-invalid={formError?.field === "duration" || undefined}
                    aria-describedby={
                      formError?.field === "duration"
                        ? "access-code-error"
                        : undefined
                    }
                    onChange={(event) => {
                      setDuration(event.target.value);
                      setFormError(null);
                    }}
                    className={FIELD}
                  />
                </label>
                <label className="block text-[13px] font-extrabold">
                  Access code expires
                  <input
                    type="datetime-local"
                    value={expiresAt}
                    aria-invalid={formError?.field === "expiresAt" || undefined}
                    aria-describedby={
                      formError?.field === "expiresAt"
                        ? "access-code-error"
                        : undefined
                    }
                    onChange={(event) => {
                      setExpiresAt(event.target.value);
                      setFormError(null);
                    }}
                    className={FIELD}
                  />
                </label>
              </div>
              {formError && (
                <p
                  id="access-code-error"
                  role="alert"
                  className="mt-[14px] border-l-4 border-red-700 pl-[10px] text-[13px] font-extrabold leading-[20px] text-red-700"
                >
                  {formError.message}
                </p>
              )}
              <div className="mt-[20px] grid grid-cols-2 gap-[10px] sm:mt-[24px] sm:flex sm:justify-end sm:gap-[12px]">
                <button
                  type="button"
                  onClick={closeGenerationDialog}
                  disabled={isGenerating}
                  className={`${BTN_GHOST} disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className={`${BTN_PRIMARY} disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  {isGenerating ? "Generating..." : "Generate"}
                </button>
              </div>
            </form>
          </div>
        )}
        <Footer />
      </div>
    </RequireAuth>
  );
};

export default MyLiveQuizzesPage;
