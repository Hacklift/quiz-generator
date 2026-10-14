"use client";
import { useTranslation } from "react-i18next";

import React from "react";
import { CONTAINER } from "@shared/ui/quizwerk";
import PersonaPicker from "@features/persona/components/PersonaPicker";

/**
 * [SCAFFOLD-OWNED] Shown when a signed-in user has no persona yet.
 *
 * Deliberately inline rather than a redirect: it makes the dashboard
 * demoable before the signup-time picker (#120) and settings editor (#122)
 * exist, and it is a reasonable permanent fallback for users who skip
 * onboarding.
 */
export default function PersonaGate() {
  const { t: uiText } = useTranslation("ui");

  return (
    <div className={`${CONTAINER} py-[clamp(32px,5vw,56px)]`}>
      <PersonaPicker heading={uiText("m261039373173ee63")} />
    </div>
  );
}
