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
      <div>
        <Kicker>Get set up</Kicker>
        <h2 className="text-[32px] font-extrabold leading-[42px] tracking-[-0.015em]">
          {heading}
        </h2>
        <div className="mt-[32px] grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-[28px]">
          {(Object.keys(PERSONA_TAXONOMY) as PersonaCategory[]).map((slug) => {
            const group = PERSONA_TAXONOMY[slug];
            return (
              <button
                key={slug}
                type="button"
                onClick={() => setCategory(slug)}
                className="border-t-2 border-divider px-[6px] py-[20px] text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                <span className="flex items-center gap-[14px]">
                  <span className="h-[8px] w-[8px] flex-none bg-brand" />
                  <span className="flex-1">
                    <span className="block text-[20px] font-extrabold leading-[1.2]">
                      {group.label}
                    </span>
                    <span className="mt-[4px] block text-[14px] text-ink/70">
                      {group.description}
                    </span>
                  </span>
                  <span aria-hidden="true" className="text-[18px]">
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
    <div>
      <Kicker>{group.label}</Kicker>
      <h2 className="text-[32px] font-extrabold leading-[42px] tracking-[-0.015em]">
        Which describes you best?
      </h2>
      <div className="mt-[28px] max-w-[560px]">
        {group.userTypes.map((definition) => (
          <button
            key={definition.slug}
            type="button"
            disabled={isSaving}
            onClick={() =>
              choose({ category, userType: definition.slug })
            }
            className="block w-full border-t-2 border-divider px-[6px] py-[16px] text-left transition hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="flex items-center gap-[14px]">
              <span className="h-[8px] w-[8px] flex-none bg-brand" />
              <span className="flex-1">
                <span className="block text-[17px] font-extrabold leading-[1.2]">
                  {definition.label}
                </span>
                <span className="mt-[3px] block text-[13.5px] text-ink/70">
                  {definition.description}
                </span>
              </span>
              <span aria-hidden="true" className="text-[18px]">
                →
              </span>
            </span>
          </button>
        ))}
      </div>
      <div className="mt-[28px] flex gap-[14px]">
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
