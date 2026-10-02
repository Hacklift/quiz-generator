import { useRouter } from "next/router";
import React, { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import {
  ParticipantRow,
  liveQuizService,
  type LiveResultsExportFormat,
} from "@features/live-quiz/api/liveQuizService";
import { downloadLiveResults } from "@features/live-quiz/lib/downloadLiveResults";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { usePersona } from "@features/persona/context/personaContext";
import { ROUTES } from "@shared/config/patterns/routes";
import {
  archivo,
  BTN_GHOST,
  BTN_PRIMARY,
  CONTAINER,
  Kicker,
} from "@shared/ui/quizwerk";

interface LiveQuizCreatorDashboardProps {
  quizId: string;
}

const CHIP =
  "inline-flex items-center border-2 px-[8px] py-[2px] text-[11px] font-extrabold uppercase tracking-[0.08em]";

const statusBadgeColor: Record<string, string> = {
  joined: "border-ink/20 bg-ink/[0.06] text-ink/75",
  in_progress: "border-brand text-brand",
  submitted: "border-green-700 text-green-700",
  completed: "border-green-700 text-green-700",
  disconnected: "border-amber-700 text-amber-700",
  timed_out: "border-red-700 text-red-700",
  expired: "border-red-700 text-red-700",
};

const statusLabel: Record<string, string> = {
  joined: "Joined",
  in_progress: "In Progress",
  submitted: "Submitted",
  completed: "Completed",
  disconnected: "Disconnected",
  timed_out: "Timed Out",
  expired: "Expired",
};

const reconnectDelays = [1000, 2000, 5000, 10000];

const PANEL =
  "border-2 border-divider bg-paper p-[20px] text-[14px] leading-[24px] text-ink/70";

const formatDateTime = (isoString: string | null | undefined): string => {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleString();
  } catch {
    return "—";
  }
};

const formatDuration = (seconds: number | null | undefined): string => {
  if (seconds == null) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
};

const progressPercent = (p: ParticipantRow): number | null => {
  if (p.progress_percentage != null) return p.progress_percentage;
  if (p.progress != null && p.total_questions > 0) {
    return (p.progress / p.total_questions) * 100;
  }
  return null;
};

function LiveQuizShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`${archivo.className} flex min-h-screen flex-col bg-paper text-ink`}
    >
      <NavBar />
      <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
        {children}
      </main>
      <Footer />
    </div>
  );
}

function BackToLiveQuizzes() {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={() => router.push(ROUTES.MY_LIVE_QUIZZES)}
      className={BTN_GHOST}
    >
      All live quizzes
    </button>
  );
}

export const LiveQuizCreatorDashboard: React.FC<
  LiveQuizCreatorDashboardProps
> = ({ quizId }) => {
  const router = useRouter();
  const { userType } = usePersona();
  const [participants, setParticipants] = useState<ParticipantRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const [exportFormat, setExportFormat] =
    useState<LiveResultsExportFormat>("csv");
  const [isExporting, setIsExporting] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const mountedRef = useRef(false);
  const shouldReconnectRef = useRef(false);

  const upsertParticipant = useCallback((participant: ParticipantRow) => {
    setParticipants((current) => {
      const index = current.findIndex(
        (row) => row.session_id === participant.session_id,
      );
      if (index === -1) return [participant, ...current];
      const next = [...current];
      next[index] = participant;
      return next;
    });
  }, []);

  const fetchParticipants = useCallback(
    async (showLoading = false) => {
      if (showLoading) setLoading(true);
      setError(null);
      try {
        const data = await liveQuizService.listParticipants(quizId);
        if (mountedRef.current) {
          setParticipants(data);
        }
      } catch (err: any) {
        if (err?.response?.status === 403) {
          setError("You are not the owner of this quiz.");
          return;
        }
        if (err?.response?.status === 404) {
          setError("Quiz not found.");
          return;
        }
        if (mountedRef.current && !showLoading) {
          setError("Could not load participants.");
        }
      } finally {
        if (mountedRef.current && showLoading) {
          setLoading(false);
        }
      }
    },
    [quizId],
  );

  useEffect(() => {
    mountedRef.current = true;
    shouldReconnectRef.current = true;
    reconnectAttemptRef.current = 0;
    void fetchParticipants(true);

    const scheduleReconnect = () => {
      if (!shouldReconnectRef.current || reconnectTimerRef.current !== null) {
        return;
      }

      const delay =
        reconnectDelays[
          Math.min(reconnectAttemptRef.current, reconnectDelays.length - 1)
        ];
      reconnectAttemptRef.current += 1;
      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        connectSocket();
      }, delay);
    };

    const connectSocket = () => {
      if (!shouldReconnectRef.current || socketRef.current) return;

      let socket: WebSocket | null = null;
      socket = liveQuizService.subscribeParticipants(
        quizId,
        (event) => {
          if (!mountedRef.current) return;
          setRealtimeConnected(true);
          setError(null);
          if (event.type === "participants_snapshot") {
            setParticipants(event.participants);
            return;
          }
          upsertParticipant(event.participant);
        },
        (event) => {
          if (socketRef.current !== socket) return;

          socketRef.current = null;
          if (!mountedRef.current || !shouldReconnectRef.current) return;

          setRealtimeConnected(false);
          if (event.code === 1008) {
            setError("Could not establish real-time updates for this quiz.");
            return;
          }
          scheduleReconnect();
        },
      );

      if (!socket) {
        setRealtimeConnected(false);
        scheduleReconnect();
        return;
      }

      socketRef.current = socket;
      socket.onopen = () => {
        if (socketRef.current !== socket || !mountedRef.current) return;
        reconnectAttemptRef.current = 0;
        setRealtimeConnected(true);
      };
    };

    connectSocket();

    return () => {
      mountedRef.current = false;
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [fetchParticipants, quizId, upsertParticipant]);

  const handleRefreshClick = () => {
    fetchParticipants(true);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await downloadLiveResults(quizId, exportFormat, "live-quiz-results");
      toast.success("Session results downloaded.");
    } catch {
      toast.error("Could not export session results.");
    } finally {
      setIsExporting(false);
    }
  };

  if (loading) {
    return (
      <LiveQuizShell>
        <p className={PANEL}>Loading participants...</p>
      </LiveQuizShell>
    );
  }

  if (error) {
    return (
      <LiveQuizShell>
        <div role="alert" className={PANEL}>
          <p className="font-extrabold text-red-700">{error}</p>
          <div className="mt-[16px]">
            <BackToLiveQuizzes />
          </div>
        </div>
      </LiveQuizShell>
    );
  }

  const totalParticipants = participants.length;
  const submittedCount = participants.filter(
    (p) =>
      p.status === "submitted" ||
      p.status === "completed" ||
      p.status === "timed_out",
  ).length;
  const inProgressCount = participants.filter(
    (p) => p.status === "in_progress",
  ).length;
  const scored = participants.filter((p) => p.percentage != null);
  const averagePercentage = scored.length
    ? scored.reduce((total, p) => total + (p.percentage as number), 0) /
      scored.length
    : null;

  const stats: Array<[string, string | number]> = [
    ["Total participants", totalParticipants],
    ["In progress", inProgressCount],
    ["Submitted", submittedCount],
    [
      "Average score",
      averagePercentage != null ? `${averagePercentage.toFixed(1)}%` : "—",
    ],
  ];

  return (
    <LiveQuizShell>
      <header className="border-b-2 border-divider pb-[28px]">
        <Kicker>Live session</Kicker>
        <div className="flex flex-wrap items-end justify-between gap-[16px]">
          <div className="min-w-0">
            <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
              Live quiz dashboard
            </h1>
            <p className="mt-[12px] flex flex-wrap items-center gap-x-[14px] gap-y-[4px] text-[14px] text-ink/70">
              <span
                className={`inline-flex items-center gap-[8px] font-extrabold ${
                  realtimeConnected ? "text-brand" : "text-amber-700"
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`h-[8px] w-[8px] ${
                    realtimeConnected
                      ? "animate-live-pulse bg-brand"
                      : "bg-amber-700"
                  }`}
                />
                {realtimeConnected ? "Real time" : "Connecting"}
              </span>
              <span className="min-w-0 break-all">
                Quiz ID <span className="font-mono">{quizId}</span>
              </span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-[12px]">
            {userType === "teacher" || userType === "lecturer" ? (
              <div className="flex items-stretch">
                <label htmlFor="results-export-format" className="sr-only">
                  Export format
                </label>
                <select
                  id="results-export-format"
                  value={exportFormat}
                  onChange={(event) =>
                    setExportFormat(
                      event.target.value as LiveResultsExportFormat,
                    )
                  }
                  className="min-h-[44px] border-2 border-r-0 border-ink bg-paper px-[10px] text-[14px] font-extrabold"
                >
                  <option value="csv">CSV</option>
                  <option value="pdf">PDF</option>
                  <option value="txt">Text</option>
                </select>
                <button
                  type="button"
                  onClick={handleExport}
                  disabled={isExporting}
                  className={`${BTN_PRIMARY} disabled:cursor-wait disabled:opacity-50`}
                >
                  {isExporting ? "Exporting…" : "Export results"}
                </button>
              </div>
            ) : null}
            <button
              type="button"
              onClick={handleRefreshClick}
              className={BTN_GHOST}
            >
              Refresh
            </button>
            <BackToLiveQuizzes />
          </div>
        </div>
      </header>

      <dl className="grid grid-cols-2 gap-[14px] pt-[28px] lg:grid-cols-4">
        {stats.map(([label, value]) => (
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

      <section aria-labelledby="participants-heading" className="pt-[36px]">
        <Kicker>Participants</Kicker>
        <h2 id="participants-heading" className="text-[20px] font-extrabold">
          Who has joined
        </h2>

        {participants.length === 0 ? (
          <div className={`${PANEL} mt-[20px]`}>
            <p className="font-extrabold text-ink">No participants yet.</p>
            <p className="mt-[4px]">
              Participants will appear here once they join the quiz.
            </p>
          </div>
        ) : (
          <div className="mt-[20px] overflow-x-auto border-2 border-divider">
            <table className="min-w-full divide-y-2 divide-divider text-left text-[13px]">
              <thead className="bg-ink text-paper">
                <tr>
                  {[
                    "Participant",
                    "Status",
                    "Score",
                    "Progress",
                    "Joined",
                    "Submitted",
                    "Duration",
                    "Results",
                  ].map((heading) => (
                    <th
                      key={heading}
                      scope="col"
                      className="whitespace-nowrap px-[14px] py-[12px] text-[12px] font-extrabold uppercase tracking-[0.06em]"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-divider">
                {participants.map((p) => {
                  const progress = progressPercent(p);
                  return (
                    <tr key={p.session_id} className="hover:bg-ink/[0.04]">
                      <td className="px-[14px] py-[12px]">
                        <span className="block whitespace-nowrap font-extrabold">
                          {p.participant_name}
                        </span>
                        <span className="block whitespace-nowrap text-[12px] text-ink/65">
                          {p.participant_email || "—"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px]">
                        <span
                          className={`${CHIP} ${
                            statusBadgeColor[p.status] ||
                            "border-ink/20 bg-ink/[0.06] text-ink/75"
                          }`}
                        >
                          {statusLabel[p.status] || p.status}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px] [font-variant-numeric:tabular-nums]">
                        {p.score != null ? (
                          <>
                            <span className="block font-extrabold">
                              {p.score} / {p.total_questions}
                            </span>
                            {p.percentage != null && (
                              <span className="block text-[12px] text-ink/65">
                                {p.percentage.toFixed(1)}%
                              </span>
                            )}
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px] [font-variant-numeric:tabular-nums]">
                        {p.progress != null ? (
                          <>
                            <div className="flex items-center gap-[8px]">
                              <div className="h-[6px] w-[72px] bg-[#e4e3e2]">
                                <div
                                  className="h-full bg-brand"
                                  style={{
                                    width: `${Math.min(100, progress ?? 0)}%`,
                                  }}
                                />
                              </div>
                              <span className="font-semibold">
                                {p.progress} / {p.total_questions}
                              </span>
                            </div>
                            {p.current_question_number ? (
                              <span className="mt-[2px] block text-[12px] text-ink/65">
                                On question {p.current_question_number} of{" "}
                                {p.total_questions}
                              </span>
                            ) : null}
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px] text-ink/70">
                        {formatDateTime(p.joined_at || p.started_at)}
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px] text-ink/70">
                        {formatDateTime(p.submitted_at)}
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px] text-ink/70 [font-variant-numeric:tabular-nums]">
                        {formatDuration(p.duration_seconds)}
                      </td>
                      <td className="whitespace-nowrap px-[14px] py-[12px]">
                        {p.submitted_at ? (
                          <button
                            type="button"
                            onClick={() =>
                              router.push(
                                ROUTES.myLiveQuizAttempt(quizId, p.session_id),
                              )
                            }
                            className="font-extrabold text-brand underline underline-offset-2 hover:text-brand-600"
                          >
                            View answers
                          </button>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </LiveQuizShell>
  );
};

const LiveQuizCreatorDashboardPage: React.FC = () => {
  const router = useRouter();
  const { quizId } = router.query;

  if (!quizId || typeof quizId !== "string") {
    return (
      <LiveQuizShell>
        {router.isReady ? (
          <div className={PANEL}>
            <p className="font-extrabold text-ink">No quiz specified.</p>
            <div className="mt-[16px]">
              <BackToLiveQuizzes />
            </div>
          </div>
        ) : (
          <p className={PANEL}>Loading...</p>
        )}
      </LiveQuizShell>
    );
  }

  return (
    <RequireAuth
      title="Live Quiz Dashboard"
      description="You need to be signed in to view the quiz dashboard."
    >
      <LiveQuizCreatorDashboard quizId={quizId} />
    </RequireAuth>
  );
};

export default LiveQuizCreatorDashboardPage;
