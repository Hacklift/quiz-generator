"use client";
import { useTranslation } from "react-i18next";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireTrainingManager from "@features/training/components/RequireTrainingManager";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import {
  trainingRunApi,
  type TrainingRunDetail,
} from "@features/training/api/trainingRunApi";
import { BTN_GHOST, BTN_PRIMARY, CONTAINER, Kicker } from "@shared/ui/quizwerk";
import { ROUTES } from "@shared/config/patterns/routes";

export default function TrainingRunDetailPage({ runId }: { runId: string }) {
  return (
    <RequireTrainingManager>
      <TrainingRunDetailContent runId={runId} />
    </RequireTrainingManager>
  );
}

function TrainingRunDetailContent({ runId }: { runId: string }) {
  const { t: uiText, i18n } = useTranslation("ui");
  const displayDate = (value?: string | null) =>
    value ? new Date(value).toLocaleString(i18n.language) : "-";
  const completionLabel = (run: TrainingRunDetail) =>
    run.assigned_count
      ? uiText("trainingStatus.progress", {
          completed: run.completed_count,
          total: run.assigned_count,
        })
      : uiText("trainingStatus.completed", { completed: run.completed_count });

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
      toast.error(error?.response?.data?.detail || uiText("mefceef08ef8afec1"));
      await router.replace(ROUTES.TRAINING_RUNS);
    } finally {
      setIsLoading(false);
    }
  }, [router, runId]);

  useEffect(() => {
    void load();
  }, [load]);

  const closeRun = async () => {
    try {
      setIsClosing(true);
      await trainingRunApi.closeRun(runId);
      setShowCloseConfirm(false);
      toast.success(uiText("m439630ff2e802e9b"));
      await load();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || uiText("mb76c8a0f87a68e1f"));
    } finally {
      setIsClosing(false);
    }
  };

  const copyLink = async () => {
    if (!run?.access_url) return;
    try {
      await navigator.clipboard.writeText(run.access_url);
      toast.success(uiText("m97decb59f3a68631"));
    } catch {
      toast.error(uiText("m9925898bf6daad51"));
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <NavBar />
      <main className={`${CONTAINER} flex-1 py-[clamp(32px,5vw,56px)]`}>
        {isLoading || !run ? (
          <div className="flex min-h-[40vh] items-center justify-center">
            <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-brand" />
          </div>
        ) : (
          <>
            <header className="border-b-2 border-divider pb-[28px]">
              <Kicker>
                {run.kind === "compliance"
                  ? uiText("md2ceb6861bc8f61a")
                  : uiText("m81759aa27185516e")}
              </Kicker>
              <div className="flex flex-wrap items-end justify-between gap-[16px]">
                <div>
                  <h1 className="text-[clamp(28px,3.6vw,40px)] font-extrabold leading-[1.08] tracking-[-0.02em]">
                    {run.title}
                  </h1>
                  <p className="mt-[12px] max-w-[58ch] text-[15.5px] leading-[28px] text-ink/[0.78]">
                    {run.status === "closed"
                      ? uiText("me9b5c6f6798d1823", {
                          value0: displayDate(run.closed_at),
                        })
                      : uiText("m2218f697e1af1a91", {
                          value0: displayDate(run.closes_at),
                        })}
                  </p>
                </div>
                <div className="flex flex-wrap gap-[12px]">
                  <button
                    type="button"
                    onClick={() => router.push(ROUTES.TRAINING_RUNS)}
                    className={BTN_GHOST}
                  >
                    {uiText("m33866ac35e69f8f5")}
                  </button>
                  {run.status === "open" && (
                    <button
                      type="button"
                      disabled={isClosing}
                      onClick={() => setShowCloseConfirm(true)}
                      className={`${BTN_PRIMARY} disabled:opacity-50`}
                    >
                      {uiText("md35eda097649f5d1")}
                    </button>
                  )}
                </div>
              </div>
            </header>
            <div className="grid gap-[36px] pt-[36px] lg:grid-cols-[minmax(0,1fr)_300px]">
              <section aria-labelledby="register-heading">
                <Kicker>{uiText("m463e12c6cbb0db05")}</Kicker>
                <h2
                  id="register-heading"
                  className="text-[20px] font-extrabold"
                >
                  {uiText("m1e626e0b496a64da")}
                </h2>
                <div className="mt-[20px] overflow-x-auto border-2 border-divider">
                  <table className="min-w-full divide-y-2 divide-divider text-left text-[13px]">
                    <thead className="bg-ink text-paper">
                      <tr>
                        <th className="px-[14px] py-[12px]">
                          {uiText("m51fac985e95345d9")}
                        </th>
                        <th className="px-[14px] py-[12px]">
                          {uiText("ma3b50c476732c740")}
                        </th>
                        <th className="px-[14px] py-[12px]">
                          {uiText("m64900440a8c9a5ed")}
                        </th>
                        <th className="px-[14px] py-[12px]">
                          {uiText("m38e5a46cbc5ad328")}
                        </th>
                        <th className="px-[14px] py-[12px]">
                          {uiText("m06e70139fcf5e5c7")}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-divider">
                      {run.completion_register.map((row) => (
                        <tr key={row.assignment_id}>
                          <td className="px-[14px] py-[12px] font-semibold">
                            {row.recipient_email ||
                              row.recipient_name ||
                              uiText("mb455fdd41601de23")}
                          </td>
                          <td className="px-[14px] py-[12px]">
                            {row.status.replace("_", " ")}
                          </td>
                          <td className="px-[14px] py-[12px]">
                            {displayDate(row.completed_at)}
                          </td>
                          <td className="px-[14px] py-[12px]">
                            {row.latest_percentage != null
                              ? uiText("mcdffc1a8fa98567b", {
                                  value0: row.latest_percentage,
                                })
                              : "-"}
                          </td>
                          <td className="px-[14px] py-[12px]">
                            {row.attempts_used}/{row.max_attempts ?? "∞"}
                          </td>
                        </tr>
                      ))}
                      {!run.completion_register.length && (
                        <tr>
                          <td
                            className="px-[14px] py-[20px] text-ink/70"
                            colSpan={5}
                          >
                            {uiText("mdbb4d3a728e00f42")}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
              <aside className="border-2 border-divider bg-paper p-[20px]">
                <Kicker>{uiText("m7bbc36905270774e")}</Kicker>
                <dl className="mt-[16px] grid gap-[14px] text-[14px]">
                  <div>
                    <dt className="font-extrabold">
                      {uiText("m557fe004f344e1cc")}
                    </dt>
                    <dd className="mt-[3px] text-ink/70">
                      {completionLabel(run)}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-extrabold">
                      {uiText("m4fc52a3c4c558b51")}
                    </dt>
                    <dd className="mt-[3px] text-ink/70">
                      {uiText("ma1542e3b3232eb95", {
                        value0: run.time_limit_minutes,
                      })}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-extrabold">
                      {uiText("me4870be7222baeef")}
                    </dt>
                    <dd className="mt-[3px] text-ink/70">
                      {run.average_score ?? "-"}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-extrabold">
                      {uiText("me1cb6d30fa3f17ee")}
                    </dt>
                    <dd className="mt-[3px] text-ink/70">
                      {displayDate(run.due_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-extrabold">
                      {uiText("mec5ba0abb717da87")}
                    </dt>
                    <dd className="mt-[3px] text-ink/70">
                      {run.access_mode === "public"
                        ? uiText("m8e99b2dff44ebdd4")
                        : uiText("m6d31fe05362dec7d")}
                    </dd>
                  </div>
                </dl>
                {run.access_mode === "public" && (
                  <button
                    type="button"
                    onClick={() => void copyLink()}
                    className={`${BTN_GHOST} mt-[20px] w-full`}
                  >
                    {uiText("md31483e209cd5b1d")}
                  </button>
                )}
              </aside>
            </div>
            {showCloseConfirm && (
              <div
                className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/55 p-[20px]"
                role="presentation"
                onClick={() => !isClosing && setShowCloseConfirm(false)}
              >
                <section
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="close-run-title"
                  className="w-full max-w-[520px] border-2 border-ink bg-paper p-[28px] shadow-2xl"
                  onClick={(event) => event.stopPropagation()}
                >
                  <Kicker>{uiText("m6718521560a676c9")}</Kicker>
                  <h2
                    id="close-run-title"
                    className="mt-[8px] text-[24px] font-extrabold"
                  >
                    {uiText("mda902dc43151d6c9")}
                  </h2>
                  <p className="mt-[14px] text-[15px] leading-[25px] text-ink/75">
                    {uiText("me8df62b0aa746248")}
                  </p>
                  <p className="mt-[12px] border-l-4 border-brand pl-[12px] text-[14px] font-bold">
                    {
                      run.completion_register.filter(
                        (row) => row.status !== "completed",
                      ).length
                    }{" "}
                    {uiText("mc0cde073e7e5fc1c")}
                    {run.completion_register.filter(
                      (row) => row.status !== "completed",
                    ).length === 1
                      ? uiText("ma8bdfde11f2443a1")
                      : uiText("m9cdade103bc6384a")}{" "}
                    {uiText("m7b997b9e9570d810")}
                  </p>
                  <div className="mt-[24px] flex flex-wrap justify-end gap-[12px]">
                    <button
                      type="button"
                      disabled={isClosing}
                      onClick={() => setShowCloseConfirm(false)}
                      className={BTN_GHOST}
                    >
                      {uiText("m19766ed6ccb2f4a3")}
                    </button>
                    <button
                      type="button"
                      disabled={isClosing}
                      onClick={() => void closeRun()}
                      className={`${BTN_PRIMARY} disabled:opacity-50`}
                    >
                      {isClosing
                        ? uiText("m8b00b3201a3c5f31")
                        : uiText("mf55ecdf00be7c84c")}
                    </button>
                  </div>
                </section>
              </div>
            )}
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
