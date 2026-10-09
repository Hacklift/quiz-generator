import React from "react";
import { type PersonaUserType } from "@shared/config/persona";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";

export interface PersonaBadgeProps {
  userType: PersonaUserType;
  className?: string;
  showDefaults?: boolean;
  audienceFallback?: string;
  appliedDefaults?: {
    audienceType: string;
    difficultyLevel: string;
    numQuestions: number;
    questionType: string;
  };
}

/** Extended "Set up for: {persona}" chip showing applied generation defaults (#133). */
export default function PersonaBadge({
  userType,
  className = "",
  showDefaults = true,
  audienceFallback = "learners",
  appliedDefaults,
}: PersonaBadgeProps) {
  const { t, roles } = usePersonaCopy();
  const definition = roles[userType];
  const defaults = appliedDefaults || definition.generationDefaults;

  const capitalize = (text: string) =>
    text.charAt(0).toUpperCase() + text.slice(1);

  const formatLabel = t(`formats.${defaults.questionType}`, {
    defaultValue: defaults.questionType,
  });
  const audienceLabel = defaults.audienceType.trim() || audienceFallback;

  return (
    <div
      className={`rounded-md border border-brand-200 bg-brand-50/60 p-3.5 text-brand-900 ${className}`}
      data-testid="persona-badge"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="inline-flex items-center gap-2 text-sm font-bold text-brand-700">
          <span className="h-2 w-2 bg-brand" aria-hidden="true" />
          {t("badge.setup", { persona: definition.label })}
        </p>
        <span className="text-xs text-brand-600">{t("badge.defaults")}</span>
      </div>

      {showDefaults ? (
        <div
          className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs"
          data-testid="persona-badge-defaults"
        >
          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">{t("badge.audience")}</span>
            <strong className="text-slate-800 font-semibold">
              {t(`audiences.${audienceLabel}`, {
                defaultValue: capitalize(audienceLabel),
              })}
            </strong>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">{t("badge.difficulty")}</span>
            <strong className="text-slate-800 font-semibold">
              {t(`difficulty.${defaults.difficultyLevel}`, {
                defaultValue: capitalize(defaults.difficultyLevel),
              })}
            </strong>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">{t("badge.format")}</span>
            <strong className="text-slate-800 font-semibold">
              {formatLabel}
            </strong>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <strong className="text-slate-800 font-semibold">
              {defaults.numQuestions}
            </strong>
            <span className="text-slate-400">
              {t("badge.questions", { count: defaults.numQuestions })}
            </span>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">{t("badge.guidance")}</span>
            <strong className="text-slate-800 font-semibold">
              {t("badge.applied")}
            </strong>
          </span>
        </div>
      ) : null}
    </div>
  );
}
