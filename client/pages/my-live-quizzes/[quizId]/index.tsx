import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import React, { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import {
  ParticipantRow,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";
import RequireAuth from "@features/auth/components/RequireAuth";

interface LiveQuizCreatorDashboardProps {
  quizId: string;
}

const statusBadgeColor: Record<string, string> = {
  joined: "bg-gray-100 text-gray-700",
  in_progress: "bg-blue-100 text-blue-700",
  submitted: "bg-green-100 text-green-700",
  completed: "bg-green-100 text-green-700",
  disconnected: "bg-amber-100 text-amber-700",
  timed_out: "bg-red-100 text-red-700",
  expired: "bg-red-100 text-red-700",
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

const LiveQuizCreatorDashboard: React.FC<LiveQuizCreatorDashboardProps> = ({
  quizId,
}) => {
  const router = useRouter();
  const [participants, setParticipants] = useState<ParticipantRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtimeConnected, setRealtimeConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

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

  const fetchParticipants = useCallback(async (showLoading = false) => {
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
  }, [quizId]);

  useEffect(() => {
    mountedRef.current = true;
    fetchParticipants(true);

    socketRef.current = liveQuizService.subscribeParticipants(
      quizId,
      (event) => {
        if (!mountedRef.current) return;
        setRealtimeConnected(true);
        if (event.type === "participants_snapshot") {
          setParticipants(event.participants);
          return;
        }
        upsertParticipant(event.participant);
      },
      () => {
        if (mountedRef.current) setRealtimeConnected(false);
      },
    );

    return () => {
      mountedRef.current = false;
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [fetchParticipants, quizId, upsertParticipant]);

  const handleRefreshClick = () => {
    fetchParticipants(true);
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
          <p className="mt-4 text-gray-600">Loading participants...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100">
        <div className="text-center">
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={() => router.push("/quiz_history")}
            className="mt-4 text-sm text-[#0a3264] hover:underline"
          >
            Back to Quiz History
          </button>
        </div>
      </div>
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

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#0F2654]">
              Live Quiz Dashboard
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              Quiz ID: <span className="font-mono">{quizId}</span>
            </p>
            <p className="mt-1 text-sm text-gray-500">
              Updates:{" "}
              <span
                className={
                  realtimeConnected ? "text-green-700" : "text-amber-700"
                }
              >
                {realtimeConnected ? "Real time" : "Connecting"}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleRefreshClick}
              className="rounded-lg bg-[#0a3264] px-4 py-2 text-sm font-medium text-white hover:bg-[#082952]"
            >
              Refresh Now
            </button>
            <button
              onClick={() => router.push("/my-live-quizzes")}
              className="text-sm text-[#0a3264] hover:underline"
            >
              Back to Live Quizzes History
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-gray-500">Total Participants</p>
            <p className="mt-1 text-3xl font-bold text-[#0F2654]">
              {totalParticipants}
            </p>
          </div>
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-gray-500">In Progress</p>
            <p className="mt-1 text-3xl font-bold text-blue-600">
              {inProgressCount}
            </p>
          </div>
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <p className="text-sm text-gray-500">Submitted</p>
            <p className="mt-1 text-3xl font-bold text-green-600">
              {submittedCount}
            </p>
          </div>
        </div>

        {/* Participants Table */}
        {participants.length === 0 ? (
          <div className="rounded-xl bg-white p-12 text-center shadow-sm">
            <p className="text-lg text-gray-500">
              No participants yet.
            </p>
            <p className="mt-2 text-sm text-gray-400">
              Participants will appear here once they join the quiz.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Progress
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Current
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Joined
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Submitted
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {participants.map((p) => (
                  <tr key={p.session_id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                      {p.participant_name}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {p.participant_email || "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          statusBadgeColor[p.status] ||
                          "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {statusLabel[p.status] || p.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                      {p.score != null
                        ? `${p.score} / ${p.total_questions}${
                            p.percentage != null
                              ? ` (${p.percentage.toFixed(1)}%)`
                              : ""
                          }`
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {p.progress != null
                        ? `${p.progress} / ${p.total_questions}${
                            p.progress_percentage != null
                              ? ` (${p.progress_percentage.toFixed(1)}%)`
                              : ""
                          }`
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {p.current_question_number
                        ? `${p.current_question_number} / ${p.total_questions}`
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDateTime(p.joined_at || p.started_at)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDateTime(p.submitted_at)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDuration(p.duration_seconds)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

const LiveQuizCreatorDashboardPage: React.FC = () => {
  const router = useRouter();
  const { quizId } = router.query;

  if (!quizId || typeof quizId !== "string") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100">
        <div className="text-center">
          <p className="text-gray-500">No quiz specified.</p>
          <button
            onClick={() => router.push("/quiz_history")}
            className="mt-4 text-sm text-[#0a3264] hover:underline"
          >
            Back to Quiz History
          </button>
        </div>
      </div>
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
