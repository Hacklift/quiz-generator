"use client";
import { useTranslation } from "react-i18next";

import React, { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { usePersona } from "@features/persona/context/personaContext";
import {
  createParentPractice,
  type ParentPracticeReady,
} from "@features/parent-practice/api/parentPracticeApi";
import {
  getPresetsForLevel,
  PARENT_PRACTICE_LEVELS,
  resolveParentPracticePreset,
  type ParentPracticeLevel,
  type ParentPracticePresetId,
} from "@features/parent-practice/config/presets";
import {
  archivo,
  BTN_GHOST,
  BTN_PRIMARY,
  CONTAINER,
  Kicker,
} from "@shared/ui/quizwerk";

const MAX_QUESTIONS = Number(
  process.env.NEXT_PUBLIC_QUIZ_GENERATION_MAX_QUESTIONS || 10,
);
const DURATION_OPTIONS = [5, 10, 15, 20, 30, 45, 60] as const;
type DurationOption = `${(typeof DURATION_OPTIONS)[number]}` | "custom";

export default function CreateParentPracticePage() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { userType, isLoading } = usePersona();
  const [level, setLevel] = useState<ParentPracticeLevel>("ages-7-9");
  const [presetId, setPresetId] = useState<ParentPracticePresetId>(
    "multiplication-tables",
  );
  const [numQuestions, setNumQuestions] = useState(10);
  const [durationOption, setDurationOption] = useState<DurationOption>("20");
  const [customDuration, setCustomDuration] = useState("25");
  const [durationError, setDurationError] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [ready, setReady] = useState<ParentPracticeReady | null>(null);
  const presets = useMemo(() => getPresetsForLevel(level), [level]);

  const selectLevel = (nextLevel: ParentPracticeLevel) => {
    const nextPresets = getPresetsForLevel(nextLevel);
    setLevel(nextLevel);
    if (!nextPresets.some((preset) => preset.id === presetId)) {
      setPresetId(nextPresets[0].id);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const durationMinutes =
      durationOption === "custom"
        ? Number(customDuration)
        : Number(durationOption);
    if (
      !Number.isInteger(durationMinutes) ||
      durationMinutes < 1 ||
      durationMinutes > 180
    ) {
      setDurationError("Enter a whole number between 1 and 180 minutes.");
      return;
    }

    setDurationError("");
    try {
      setIsCreating(true);
      const params = resolveParentPracticePreset(level, presetId, numQuestions);
      setReady(await createParentPractice(params, durationMinutes));
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not create practice.",
      );
    } finally {
      setIsCreating(false);
    }
  };

  const joinPath = ready ? `/quiz-access/${ready.accessCode}` : "";
  const copyLink = async () => {
    if (!ready) return;
    await navigator.clipboard.writeText(`${window.location.origin}${joinPath}`);
    toast.success(uiText("m735df69f94073fe7"));
  };

  return (
    <RequireAuth
      title={uiText("m1bde3275776228b6")}
      description={uiText("m52772f57ef1149dd")}
    >
      <div
        className={`${archivo.className} flex min-h-screen flex-col bg-paper text-ink`}
      >
        <NavBar />
        <main className={`${CONTAINER} flex-grow py-[clamp(32px,5vw,56px)]`}>
          {isLoading ? (
            <p>{uiText("mba3bbbe10d8bef66")}</p>
          ) : userType !== "parent" ? (
            <section className="border-t-2 border-divider pt-[28px]">
              <h1 className="text-[28px] font-extrabold">
                {uiText("mcd5060878a6f9118")}
              </h1>
              <p className="mt-[12px] text-ink/70">
                {uiText("ma1dee8f20efcc7ad")}
              </p>
              <button
                className={`${BTN_GHOST} mt-[20px]`}
                onClick={() => router.push("/dashboard")}
              >
                {uiText("mb59e0c1cc1e1faf9")}
              </button>
            </section>
          ) : ready ? (
            <section
              aria-label={uiText("m177a7d9852e0f679")}
              className="max-w-[720px] border-t-2 border-divider pt-[28px]"
            >
              <Kicker>{uiText("m177a7d9852e0f679")}</Kicker>
              <h1 className="text-[clamp(28px,4vw,40px)] font-extrabold">
                {ready.title}
              </h1>
              <p className="mt-[12px] text-[16px] text-ink/70">
                {ready.questionCount} {uiText("m9f969d819e953b67")}
                {ready.durationMinutes} {uiText("m55d41a2abc35897e")}
                {ready.accessCode}
              </p>
              <div className="mt-[28px] flex flex-wrap gap-[12px]">
                <button
                  className={BTN_PRIMARY}
                  onClick={() => router.push(joinPath)}
                >
                  {uiText("md25bea8b2a2f3acd")}
                </button>
                <button className={BTN_GHOST} onClick={copyLink}>
                  {uiText("m1bba6ac927612b41")}
                </button>
              </div>
            </section>
          ) : (
            <section className="max-w-[720px]">
              <Kicker>{uiText("mcd5060878a6f9118")}</Kicker>
              <h1 className="text-[clamp(28px,4vw,40px)] font-extrabold">
                {uiText("m47255e634241fc6a")}
              </h1>
              <p className="mt-[12px] max-w-[52ch] leading-[27px] text-ink/70">
                {uiText("mcdf58e76905e28a1")}
              </p>
              <form
                noValidate
                onSubmit={submit}
                className="mt-[32px] space-y-[24px] border-t-2 border-divider pt-[28px]"
              >
                <label className="block text-[14px] font-extrabold">
                  {uiText("mb131e0b394db9475")}
                  <select
                    aria-label={uiText("mb131e0b394db9475")}
                    value={level}
                    onChange={(event) =>
                      selectLevel(event.target.value as ParentPracticeLevel)
                    }
                    className="mt-[8px] block w-full border-2 border-divider bg-paper px-[12px] py-[11px] font-normal"
                  >
                    {PARENT_PRACTICE_LEVELS.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-[14px] font-extrabold">
                  {uiText("ma4b05b03854ab340")}
                  <select
                    aria-label={uiText("ma4b05b03854ab340")}
                    value={presetId}
                    onChange={(event) =>
                      setPresetId(event.target.value as ParentPracticePresetId)
                    }
                    className="mt-[8px] block w-full border-2 border-divider bg-paper px-[12px] py-[11px] font-normal"
                  >
                    {presets.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-[14px] font-extrabold">
                  {uiText("m4bbde39fcd87f7de")}
                  <input
                    aria-label={uiText("m4bbde39fcd87f7de")}
                    type="number"
                    min={1}
                    max={MAX_QUESTIONS}
                    value={numQuestions}
                    onChange={(event) =>
                      setNumQuestions(
                        Math.min(
                          MAX_QUESTIONS,
                          Math.max(1, Number(event.target.value)),
                        ),
                      )
                    }
                    className="mt-[8px] block w-full border-2 border-divider bg-paper px-[12px] py-[11px] font-normal"
                  />
                </label>
                <div>
                  <label className="block text-[14px] font-extrabold">
                    {uiText("m4fc52a3c4c558b51")}
                    <select
                      aria-label={uiText("m4fc52a3c4c558b51")}
                      value={durationOption}
                      onChange={(event) => {
                        setDurationOption(event.target.value as DurationOption);
                        setDurationError("");
                      }}
                      className="mt-[8px] block w-full border-2 border-divider bg-paper px-[12px] py-[11px] font-normal"
                    >
                      {DURATION_OPTIONS.map((minutes) => (
                        <option key={minutes} value={minutes}>
                          {minutes} {uiText("m90e63d85fa1ab2c8")}
                        </option>
                      ))}
                      <option value="custom">
                        {uiText("m494ca78f7374e46f")}
                      </option>
                    </select>
                  </label>
                  {durationOption === "custom" ? (
                    <label className="mt-[16px] block text-[14px] font-extrabold">
                      {uiText("m37421efc80dd02c1")}
                      <span className="mt-[8px] flex items-center gap-[10px] font-normal">
                        <input
                          aria-label={uiText("m37421efc80dd02c1")}
                          type="number"
                          min={1}
                          max={180}
                          step={1}
                          value={customDuration}
                          onChange={(event) => {
                            setCustomDuration(event.target.value);
                            setDurationError("");
                          }}
                          aria-invalid={Boolean(durationError)}
                          aria-describedby="duration-error"
                          className="w-[140px] border-2 border-divider bg-paper px-[12px] py-[11px]"
                        />
                        {uiText("m90e63d85fa1ab2c8")}
                      </span>
                    </label>
                  ) : null}
                  {durationError ? (
                    <p
                      id="duration-error"
                      role="alert"
                      className="mt-[8px] text-[13px] font-normal text-red-700"
                    >
                      {durationError}
                    </p>
                  ) : null}
                </div>
                <button
                  type="submit"
                  disabled={isCreating}
                  className={`${BTN_PRIMARY} disabled:cursor-not-allowed disabled:opacity-60`}
                >
                  {isCreating
                    ? uiText("mc79ed9492e3c1719")
                    : uiText("m92c7e9ad52f12b83")}
                </button>
              </form>
            </section>
          )}
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
