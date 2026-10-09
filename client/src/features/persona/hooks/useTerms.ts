"use client";

import { useCallback } from "react";
import { usePersona } from "@features/persona/context/personaContext";
import {
  termMessageKey,
  type TermForm,
  type TermKey,
} from "@shared/config/terminology";
import { useTranslation } from "react-i18next";
import "@features/locale/i18n";

/**
 * Persona-bound terminology.
 *
 *   const t = useTerms();
 *   t("learner", "plural")   // "students" for a teacher, "team members" for HR
 *
 * Persona views must use this instead of hardcoding learner/class/team nouns.
 */
export function useTerms() {
  const { persona } = usePersona();
  const { t } = useTranslation("persona");

  return useCallback(
    (key: TermKey, form: TermForm = "singular") =>
      t(termMessageKey(key, persona, form)),
    [t, persona],
  );
}
