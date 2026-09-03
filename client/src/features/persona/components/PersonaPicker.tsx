"use client";

import React, { useState } from "react";
import toast from "react-hot-toast";
import {
  PERSONA_TAXONOMY,
  type Persona,
  type PersonaCategory,
} from "@shared/config/persona";
import { BTN_GHOST, BTN_PRIMARY, Kicker } from "@shared/ui/quizwerk";
import { usePersona } from "@features/persona/context/personaContext";
import type { PersonaWriteSource } from "@features/persona/types/persona";

/**
 * Two-step category -> user-type picker, styled to the Quizwerk system.
 *
 * Shared by the dashboard's unset state, the signup onboarding flow (#120)
 * and profile settings (#122) — don't fork it.
 */
export default function PersonaPicker({
  onPicked,
  heading = "Who are you setting up for?",
  initialCategory = null,
  source = "profile",
}: {
  onPicked?: (persona: Persona) => void;
  heading?: string;
  initialCategory?: PersonaCategory | null;
  source?: PersonaWriteSource;
}) {
  const { setPersona } = usePersona();
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
      toast.error("Could not save your choice. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  if (!category) {
    return (
      <div className="w-full max-w-full">
        <Kicker>Get set up</Kicker>
        <h2 className="text-[clamp(22px,5vw,32px)] font-extrabold leading-tight tracking-[-0.02em]">
          {heading}
        </h2>
        <div className="mt-6 sm:mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 w-full max-w-full">
          {(Object.keys(PERSONA_TAXONOMY) as PersonaCategory[]).map((slug) => {
            const group = PERSONA_TAXONOMY[slug];
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
                    <span className="block break-words text-lg font-extrabold leading-[1.2] sm:text-[20px]">
                      {group.label}
                    </span>
                    <span className="mt-1 block text-xs sm:text-[14px] text-ink/70">
                      {group.description}
                    </span>
                  </span>
                  <span aria-hidden="true" className="text-base sm:text-[18px] flex-none">
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

  const group = PERSONA_TAXONOMY[category];

  return (
    <div className="w-full max-w-full">
      <Kicker>{group.label}</Kicker>
      <h2 className="text-[clamp(22px,5vw,32px)] font-extrabold leading-tight tracking-[-0.02em]">
        Which describes you best?
      </h2>
      <div className="mt-6 sm:mt-8 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 w-full max-w-none">
        {group.userTypes.map((definition) => (
          <button
            key={definition.slug}
            type="button"
            disabled={isSaving}
            onClick={() =>
              choose({ category, userType: definition.slug })
            }
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
              <span aria-hidden="true" className="text-base sm:text-[18px] flex-none">
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
          Back
        </button>
        {isSaving ? <span className={BTN_PRIMARY}>Saving…</span> : null}
      </div>
    </div>
  );
}
