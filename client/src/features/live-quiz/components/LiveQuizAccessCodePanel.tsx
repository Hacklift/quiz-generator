import { useTranslation } from "react-i18next";
import React, { FormEvent, useState } from "react";
import toast from "react-hot-toast";
import { TokenService } from "@shared/auth/tokenService";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";

interface LiveQuizAccessCodePanelProps {
  quizId?: string;
}

const tomorrowLocalValue = () => {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};

const LiveQuizAccessCodePanel: React.FC<LiveQuizAccessCodePanelProps> = ({
  quizId,
}) => {
  const { t: uiText } = useTranslation("ui");

  const [duration, setDuration] = useState(20);
  const [expiresAt, setExpiresAt] = useState(tomorrowLocalValue());
  const [participantAccessMode, setParticipantAccessMode] = useState<
    "public" | "restricted" | "invited_only"
  >("public");
  const [invitedEmailsText, setInvitedEmailsText] = useState("");
  const [sendEmailInvitations, setSendEmailInvitations] = useState(false);
  const [accessCode, setAccessCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  if (!quizId || !TokenService.hasTokens()) return null;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const invitedEmails = invitedEmailsText
      .split(/[\s,;]+/)
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean);

    if (
      (participantAccessMode === "restricted" ||
        participantAccessMode === "invited_only") &&
      invitedEmails.length === 0
    ) {
      toast.error(uiText("m65a4f2d4dd83e5ec"));
      return;
    }

    try {
      setIsLoading(true);
      const response = await liveQuizService.createAccessCode({
        quizId,
        time_limit_minutes: duration,
        access_code_expires_at: new Date(expiresAt).toISOString(),
        participant_access_mode: participantAccessMode,
        invited_emails: invitedEmails,
        send_email_invitations: sendEmailInvitations,
      });
      setAccessCode(response.access_code);
      const sentCount =
        response.invitations_queued || response.invitations_delivered;
      toast.success(
        response.invitations_created
          ? `Live quiz ready. ${sentCount} invitation email(s) ${
              response.invitations_queued ? "queued" : "delivered"
            }.`
          : "Live quiz access code generated.",
      );
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not generate access code.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const accessUrl =
    typeof window !== "undefined" && accessCode
      ? `${window.location.origin}/quiz-access/${accessCode}`
      : "";

  return (
    <section className="rounded-md border border-slate-200 bg-white px-4 py-5 shadow-sm">
      <h2 className="text-lg font-bold text-[#0F2654]">
        {uiText("mb34cb0aed279e420")}
      </h2>
      <form onSubmit={handleSubmit} className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="block text-sm font-semibold text-slate-700">
          {uiText("m471195f5d126bfed")}
          <input
            type="number"
            min={1}
            max={1440}
            value={duration}
            onChange={(event) => setDuration(Number(event.target.value))}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="block text-sm font-semibold text-slate-700">
          {uiText("m6e5ab5d97b456f1c")}
          <input
            type="datetime-local"
            value={expiresAt}
            onChange={(event) => setExpiresAt(event.target.value)}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="block text-sm font-semibold text-slate-700">
          {uiText("m6ab7c606d3128746")}
          <select
            value={participantAccessMode}
            onChange={(event) =>
              setParticipantAccessMode(
                event.target.value as "public" | "restricted" | "invited_only",
              )
            }
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
          >
            <option value="public">{uiText("m178b790b1cb2c176")}</option>
            <option value="restricted">{uiText("m0c906cdd09708c8b")}</option>
            <option value="invited_only">{uiText("mf9636e9a7397b7af")}</option>
          </select>
        </label>
        <label className="block text-sm font-semibold text-slate-700 md:col-span-2">
          {uiText("m26f1e46c9dfb0e3f")}
          <textarea
            value={invitedEmailsText}
            onChange={(event) => setInvitedEmailsText(event.target.value)}
            placeholder={uiText("mefe42627ddbff54d")}
            rows={3}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
          />
        </label>
        <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <input
            type="checkbox"
            checked={sendEmailInvitations}
            onChange={(event) => setSendEmailInvitations(event.target.checked)}
            className="h-4 w-4 accent-[#0F2654]"
          />
          {uiText("ma04fe96c22a26440")}
        </label>
        <button
          type="submit"
          disabled={isLoading}
          className="self-end rounded-md bg-[#0a3264] px-4 py-2 text-sm font-semibold text-white hover:bg-[#082952] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading
            ? uiText("m49286f33b674a0a6")
            : uiText("m828abc2dd1b3b70c")}
        </button>
      </form>

      {accessCode && (
        <div className="mt-4 rounded-md bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-600">
            {uiText("mdb76a756cec85e60")}
          </p>
          <p className="mt-1 text-2xl font-bold tracking-widest text-[#0F2654]">
            {accessCode}
          </p>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(accessUrl);
              toast.success(uiText("mc0a1b867714c680f"));
            }}
            className="mt-3 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-white"
          >
            {uiText("m724e78a3254c899d")}
          </button>
        </div>
      )}
    </section>
  );
};

export default LiveQuizAccessCodePanel;
