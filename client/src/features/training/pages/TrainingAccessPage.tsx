import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import React, { FormEvent, useEffect, useState } from "react";
import toast from "react-hot-toast";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { saveParticipantToken } from "@features/live-quiz/api/liveQuizService";
import { trainingAccessApi } from "@features/training/api/trainingAccessApi";
import type { TrainingAccessPreview } from "@features/training/api/trainingRunApi";

export default function TrainingAccessPage({ code }: { code: string }) {
  const router = useRouter();
  const [preview, setPreview] = useState<TrainingAccessPreview | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    void trainingAccessApi.preview(code).then(setPreview).catch(async (error) => {
      toast.error(error?.response?.data?.detail || "Training link unavailable.");
      await router.replace("/");
    });
  }, [code, router]);

  const start = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) { toast.error("Enter your full name."); return; }
    try {
      setIsStarting(true);
      const session = await trainingAccessApi.start({ code, participant_name: name.trim(), participant_email: email.trim() || undefined });
      saveParticipantToken(session.session_id, session.participant_token);
      await router.push(session.redirect_url);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not start training.");
    } finally { setIsStarting(false); }
  };

  if (!preview) return <div className="flex min-h-screen items-center justify-center bg-slate-100"><div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" /></div>;
  return <div className="flex min-h-screen flex-col bg-slate-100"><NavBar /><main className="flex flex-1 items-center justify-center px-4 py-10"><form onSubmit={start} className="w-full max-w-xl rounded-md border border-slate-200 bg-white p-6 shadow-sm"><p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Training session</p><h1 className="mt-2 text-2xl font-bold text-[#0F2654]">{preview.title}</h1><div className="mt-5 grid gap-3 text-sm text-slate-700 sm:grid-cols-3"><div className="rounded-md bg-slate-50 p-3"><span className="block font-semibold">Questions</span>{preview.total_questions}</div><div className="rounded-md bg-slate-50 p-3"><span className="block font-semibold">Duration</span>{preview.time_limit_minutes} minutes</div><div className="rounded-md bg-slate-50 p-3"><span className="block font-semibold">Closes</span>{new Date(preview.closes_at).toLocaleDateString()}</div></div><label className="mt-6 block text-sm font-semibold text-slate-700">Full name<input value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100" /></label><label className="mt-4 block text-sm font-semibold text-slate-700">Email (optional)<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100" /></label><button type="submit" disabled={isStarting} className="mt-6 w-full rounded-md bg-[#0a3264] px-4 py-2 text-sm font-semibold text-white hover:bg-[#082952] disabled:cursor-not-allowed disabled:opacity-60">{isStarting ? "Starting..." : "Start training"}</button></form></main><Footer /></div>;
}

export const getServerSideProps: GetServerSideProps<{ code: string }> = async ({ params }) => ({ props: { code: String(params?.code || "") } });
