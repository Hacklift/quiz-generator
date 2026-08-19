"use client";

import { useCallback } from "react";
import { usePersona } from "@features/persona/context/personaContext";
import {
  resolveTerm,
  type TermForm,
  type TermKey,
} from "@shared/config/terminology";

/**
 * Persona-bound terminology.
 *
 *   const t = useTerms();
 *   t("learner", "plural")   // "students" for a teacher, "employees" for HR
 *
 * Persona views must use this instead of hardcoding learner/class/team nouns.
 */
export function useTerms() {
  const { persona } = usePersona();

  return useCallback(
    (key: TermKey, form: TermForm = "singular") =>
      resolveTerm(key, persona, form),
    [persona],
  );
}
