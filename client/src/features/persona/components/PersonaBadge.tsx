import React from "react";
import {
  getUserTypeDefinition,
  type PersonaUserType,
} from "@shared/config/persona";

const FORMAT_LABELS: Record<string, string> = {
  multichoice: "Multiple Choice",
  "true-false": "True/False",
  "short-answer": "Short Answer",
  "open-ended": "Open Ended",
};

export interface PersonaBadgeProps {
  userType: PersonaUserType;
  className?: string;
  showDefaults?: boolean;
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
  appliedDefaults,
}: PersonaBadgeProps) {
  const definition = getUserTypeDefinition(userType);
  const defaults = appliedDefaults || definition.generationDefaults;

  const capitalize = (text: string) =>
    text.charAt(0).toUpperCase() + text.slice(1);

  const formatLabel =
    FORMAT_LABELS[defaults.questionType] || defaults.questionType;

  return (
    <div
      className={`rounded-md border border-brand-200 bg-brand-50/60 p-3.5 text-brand-900 ${className}`}
      data-testid="persona-badge"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="inline-flex items-center gap-2 text-sm font-bold text-brand-700">
          <span className="h-2 w-2 bg-brand" aria-hidden="true" />
          Set up for: {definition.label}
        </p>
        <span className="text-xs text-brand-600">Persona defaults applied</span>
      </div>

      {showDefaults ? (
        <div
          className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs"
          data-testid="persona-badge-defaults"
        >
          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">Audience:</span>
            <strong className="text-slate-800 font-semibold">
              {capitalize(defaults.audienceType)}
            </strong>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">Difficulty:</span>
            <strong className="text-slate-800 font-semibold">
              {capitalize(defaults.difficultyLevel)}
            </strong>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">Format:</span>
            <strong className="text-slate-800 font-semibold">{formatLabel}</strong>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <strong className="text-slate-800 font-semibold">
              {defaults.numQuestions}
            </strong>
            <span className="text-slate-400">questions</span>
          </span>

          <span className="inline-flex items-center gap-1 rounded bg-white px-2 py-0.5 font-medium text-slate-700 shadow-xs border border-slate-200">
            <span className="text-slate-400">Guidance:</span>
            <strong className="text-slate-800 font-semibold">Applied</strong>
          </span>
        </div>
      ) : null}
    </div>
  );
}
