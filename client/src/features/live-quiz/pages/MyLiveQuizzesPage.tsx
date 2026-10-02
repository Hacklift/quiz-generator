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
  Microlabel,
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

const isExpired = (expiresAt: string | null | undefined) =>
  !expiresAt || new Date(expiresAt).getTime() <= Date.now();

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

const PANEL =
  "border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70";

export const MyLiveQuizzesPage: React.FC = () => {
  const router = useRouter();
  const [quizzes, setQuizzes] = useState<LiveQuizSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [quizToGenerateFor, setQuizToGenerateFor] =
    useState<LiveQuizSummary | null>(null);
  const [duration, setDuration] = useState(20);
  const [expiresAt, setExpiresAt] = useState(tomorrowLocalValue());
  const [isGenerating, setIsGenerating] = useState(false);
  const [exportingQuizId, setExportingQuizId] = useState<string | null>(null);
  const [openActionsQuizId, setOpenActionsQuizId] = useState<string | null>(
    null,
  );
  const actionsMenuRef = useRef<HTMLDivElement | null>(null);

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
      if (event.key === "Escape") setOpenActionsQuizId(null);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openActionsQuizId]);

  const openGenerationDialog = (quiz: LiveQuizSummary) => {
    setQuizToGenerateFor(quiz);
    setDuration(quiz.time_limit_minutes || 20);
    setExpiresAt(tomorrowLocalValue());
  };

  const generateAccessCode = async (event: FormEvent) => {
    event.preventDefault();
    if (!quizToGenerateFor) return;

    try {
      setIsGenerating(true);
      const response = await liveQuizService.createAccessCode({
        quizId: quizToGenerateFor.quiz_id,
        time_limit_minutes: duration,
        access_code_expires_at: new Date(expiresAt).toISOString(),
        participant_access_mode:
          quizToGenerateFor.participant_access_mode || "public",
        invited_emails: quizToGenerateFor.invited_emails || [],
      });
      setQuizToGenerateFor(null);
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
    try {
      await downloadLiveResults(
        quiz.quiz_id,
        format,
        `${quiz.title || "live-quiz"}-results`,
      );
      toast.success("Session results downloaded.");
    } catch {
      toast.error("Could not export session results.");
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
        <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
          <header className="border-b-2 border-divider pb-[28px]">
            <Kicker>Live quizzes</Kicker>
            <div className="flex flex-wrap items-end justify-between gap-[16px]">
              <div>
                <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
                  Your live sessions
                </h1>
                <p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
                  Generate access codes, watch participants join, and export
                  results when a session ends.
                </p>
              </div>
              <div className="flex flex-wrap gap-[12px]">
                <button
                  type="button"
                  onClick={() => void loadLiveQuizzes()}
                  disabled={isLoading}
                  className={`${BTN_GHOST} disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={() => router.push(ROUTES.GENERATE)}
                  className={BTN_PRIMARY}
                >
                  Create quiz
                </button>
              </div>
            </div>
          </header>

          {!isLoading && quizzes.length > 0 && (
            <dl className="grid gap-[14px] pt-[28px] sm:grid-cols-3">
              {[
                ["Live quizzes", quizzes.length],
                ["Open access codes", openCodeCount],
                ["Participants", participantTotal],
              ].map(([label, value]) => (
                <div key={label} className="border-t-2 border-divider pt-[14px]">
                  <dt className="text-[12px] font-extrabold uppercase tracking-[0.08em] text-ink/60">
                    {label}
                  </dt>
                  <dd className="mt-[4px] text-[30px] font-extrabold [font-variant-numeric:tabular-nums]">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          )}

          <section aria-labelledby="sessions-heading" className="pt-[36px]">
            <Kicker>All sessions</Kicker>
            <h2 id="sessions-heading" className="text-[20px] font-extrabold">
              Quizzes and access codes
            </h2>

            <div className="mt-[20px]">
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
                    className={`${BTN_PRIMARY} mt-[16px]`}
                  >
                    Create quiz
                  </button>
                </div>
              ) : (
                <ul className="grid gap-[12px]">
                  {quizzes.map((quiz) => {
                    const codeExpired = isExpired(quiz.access_code_expires_at);
                    const isMenuOpen = openActionsQuizId === quiz.quiz_id;
                    return (
                      <li
                        key={quiz.quiz_id}
                        className="grid gap-[18px] border-2 border-divider bg-paper p-[16px] transition hover:border-ink/60 sm:p-[20px] lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.9fr)_minmax(0,1fr)_auto] lg:items-center"
                      >
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
                          <h3 className="mt-[10px] break-words text-[17px] font-extrabold leading-[1.3]">
                            {quiz.title}
                          </h3>
                          <p className="mt-[3px] text-[13px] text-ink/65">
                            Created {formatDateTime(quiz.created_at)}
                          </p>
                        </div>

                        <div>
                          <Microlabel>Access code</Microlabel>
                          {quiz.access_code ? (
                            <>
                              <p
                                className={`font-mono text-[20px] font-extrabold tracking-[0.12em] ${
                                  codeExpired ? "text-ink/40 line-through" : ""
                                }`}
                              >
                                {quiz.access_code}
                              </p>
                              <p
                                className={`mt-[2px] text-[12px] ${
                                  codeExpired
                                    ? "font-extrabold text-red-700"
                                    : "text-ink/65"
                                }`}
                              >
                                {codeExpired ? "Expired" : "Expires"}{" "}
                                {formatDateTime(quiz.access_code_expires_at)}
                              </p>
                            </>
                          ) : (
                            <p className="text-[14px] text-ink/65">No code yet</p>
                          )}
                        </div>

                        <dl className="grid grid-cols-3 gap-[12px]">
                          {[
                            ["Joined", quiz.participant_count],
                            ["Completed", quiz.completed_count],
                            ["Avg score", quiz.average_score ?? "-"],
                          ].map(([label, value]) => (
                            <div key={label}>
                              <dt className="text-[11px] font-extrabold uppercase tracking-[0.1em] text-ink/60">
                                {label}
                              </dt>
                              <dd className="mt-[2px] text-[18px] font-extrabold [font-variant-numeric:tabular-nums]">
                                {value}
                              </dd>
                            </div>
                          ))}
                        </dl>

                        <div className="flex flex-wrap items-center gap-[8px] lg:justify-end">
                          {(!quiz.access_code || codeExpired) && (
                            <button
                              type="button"
                              onClick={() => openGenerationDialog(quiz)}
                              className={BTN_PRIMARY}
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
                            className={BTN_GHOST}
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
                              className={`${BTN_GHOST} w-[44px] text-[20px] leading-none disabled:cursor-wait disabled:opacity-50`}
                            >
                              &#8942;
                            </button>
                            {isMenuOpen && (
                              <div
                                className="absolute right-0 z-20 mt-[6px] w-[190px] border-2 border-ink bg-paper py-[8px] text-left"
                              >
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
            className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/55 p-[20px]"
            role="presentation"
            onClick={() => !isGenerating && setQuizToGenerateFor(null)}
          >
            <form
              role="dialog"
              aria-modal="true"
              aria-labelledby="access-code-title"
              onSubmit={generateAccessCode}
              onClick={(event) => event.stopPropagation()}
              className="w-full max-w-[480px] border-2 border-ink bg-paper p-[24px] sm:p-[28px]"
            >
              <Kicker>Access code</Kicker>
              <h2
                id="access-code-title"
                className="text-[24px] font-extrabold leading-[1.15]"
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
                    type="number"
                    min={1}
                    max={1440}
                    value={duration}
                    onChange={(event) =>
                      setDuration(Number(event.target.value))
                    }
                    className={FIELD}
                  />
                </label>
                <label className="block text-[13px] font-extrabold">
                  Access code expires
                  <input
                    type="datetime-local"
                    value={expiresAt}
                    onChange={(event) => setExpiresAt(event.target.value)}
                    className={FIELD}
                  />
                </label>
              </div>
              <div className="mt-[24px] flex flex-wrap justify-end gap-[12px]">
                <button
                  type="button"
                  onClick={() => setQuizToGenerateFor(null)}
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
