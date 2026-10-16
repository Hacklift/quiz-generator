"use client";

import React, { useState } from "react";
import toast from "react-hot-toast";
import {
  PERSONA_CATEGORIES,
  type Persona,
  type PersonaCategory,
} from "@shared/config/persona";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { usePersona } from "@features/persona/context/personaContext";
import type { PersonaWriteSource } from "@features/persona/types/persona";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";

/**
 * Two-step category -> user-type picker, styled to the Quizwerk system.
 *
 * Shared by the dashboard's unset state, the signup onboarding flow (#120)
 * and profile settings (#122) — don't fork it.
 */
export default function PersonaPicker({
  onPicked,
  heading,
  initialCategory = null,
  source = "profile",
}: {
  onPicked?: (persona: Persona) => void;
  heading?: string;
  initialCategory?: PersonaCategory | null;
  source?: PersonaWriteSource;
}) {
  const { setPersona } = usePersona();
  const { t, categories } = usePersonaCopy();
  const [category, setCategory] = useState<PersonaCategory | null>(
    initialCategory,
  );
  const [isSaving, setIsSaving] = useState(false);

  const choose = async (persona: Persona) => {
    setIsSaving(true);
    try {
      await setPersona(persona, { source });
      onPicked?.(persona);
    } catch {
      toast.error(t("picker.error"));
    } finally {
      setIsSaving(false);
    }
  };

  if (!category) {
    return (
      <div className="w-full max-w-full">
        <Kicker>{t("picker.setup")}</Kicker>
        <h2 className="text-lg sm:text-xl font-extrabold leading-snug tracking-[-0.015em]">
          {heading ?? t("picker.heading")}
        </h2>
        <div className="mt-4 sm:mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-6 w-full max-w-full">
          {PERSONA_CATEGORIES.map((slug) => {
            const group = categories[slug];
            return (
              <button
                key={slug}
                type="button"
                onClick={() => setCategory(slug)}
                className="border-t-2 border-divider px-2 sm:px-3 py-4 sm:py-5 text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand w-full"
              >
                <span className="flex items-center gap-3 sm:gap-[14px]">
                  <span className="h-2 w-2 flex-none bg-brand" />
                  <span className="flex-1 min-w-0">
                    <span className="block break-words text-base font-extrabold leading-[1.2] sm:text-[18px]">
                      {group.label}
                    </span>
                    <span className="mt-1 block text-xs sm:text-[14px] text-ink/70">
                      {group.description}
                    </span>
                  </span>
                  <span
                    aria-hidden="true"
                    className="text-base sm:text-[18px] flex-none"
                  >
                    →
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  const group = categories[category];

  return (
    <div className="w-full max-w-full">
      <Kicker>{group.label}</Kicker>
      <h2 className="text-lg sm:text-xl font-extrabold leading-snug tracking-[-0.015em]">
        {t("picker.role")}
      </h2>
      <div className="mt-4 sm:mt-6 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 w-full max-w-none">
        {group.userTypes.map((definition) => (
          <button
            key={definition.slug}
            type="button"
            disabled={isSaving}
            onClick={() => choose({ category, userType: definition.slug })}
            className="w-full border-t-2 border-divider px-2 sm:px-3 py-3.5 sm:py-4 text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="flex items-center gap-3 sm:gap-[14px]">
              <span className="h-2 w-2 flex-none bg-brand" />
              <span className="flex-1 min-w-0">
                <span className="block text-base sm:text-[17px] font-extrabold leading-[1.2]">
                  {definition.label}
                </span>
                <span className="mt-1 block text-xs sm:text-[13.5px] text-ink/70">
                  {definition.description}
                </span>
              </span>
              <span
                aria-hidden="true"
                className="text-base sm:text-[18px] flex-none"
              >
                →
              </span>
            </span>
          </button>
        ))}
      </div>
      <div className="mt-6 sm:mt-8 flex gap-3">
        <button
          type="button"
          onClick={() => setCategory(null)}
          className={BTN_GHOST}
        >
          {t("picker.back")}
        </button>
        {isSaving ? (
          <span className={BTN_PRIMARY}>{t("picker.saving")}</span>
        ) : null}
      </div>
    </div>
  );
}
