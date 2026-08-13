"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/router";
import { useAuth } from "@features/auth/context/authContext";
import PersonaPicker from "@features/persona/components/PersonaPicker";
import { usePersona } from "@features/persona/context/personaContext";
import {
  readPersonaOnboardingSkipped,
  writePersonaOnboardingSkipped,
} from "@features/persona/lib/personaOnboardingStorage";
import { parsePersona } from "@shared/config/persona";
import { BTN_GHOST, CONTAINER } from "@shared/ui/quizwerk";

const SUPPRESSED_ROUTES = ["/auth"];

export default function PersonaOnboardingGate() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const { persona, source, setPersona } = usePersona();
  const [skipState, setSkipState] = useState<{
    userId: string;
    skipped: boolean;
  } | null>(null);
  const [isAutoSaving, setIsAutoSaving] = useState(false);
  const failedAutoSaveKeys = useRef<Set<string>>(new Set());
  const pendingAutoSaveKey = useRef<string | null>(null);

  const profilePersona = useMemo(
    () =>
      user
        ? parsePersona(user.persona_category, user.persona_user_type)
        : null,
    [user],
  );

  useEffect(() => {
    if (!user?.id) {
      setSkipState(null);
      return;
    }

    setSkipState({
      userId: user.id,
      skipped: readPersonaOnboardingSkipped(user.id),
    });
  }, [user?.id]);

  const autoSaveKey = persona
    ? `${user?.id ?? "anonymous"}:${source}:${persona.category}:${persona.userType}`
    : null;

  useEffect(() => {
    if (
      isLoading ||
      !isAuthenticated ||
      !user ||
      profilePersona ||
      !persona ||
      (source !== "query" && source !== "storage") ||
      !autoSaveKey ||
      pendingAutoSaveKey.current === autoSaveKey ||
      failedAutoSaveKeys.current.has(autoSaveKey)
    ) {
      return;
    }

    pendingAutoSaveKey.current = autoSaveKey;
    setIsAutoSaving(true);

    void setPersona(persona, { source: "inferred" })
      .catch((error) => {
        failedAutoSaveKeys.current.add(autoSaveKey);
        console.warn("Failed to persist carried persona", error);
      })
      .finally(() => {
        if (pendingAutoSaveKey.current === autoSaveKey) {
          pendingAutoSaveKey.current = null;
        }
        setIsAutoSaving(false);
      });
  }, [
    autoSaveKey,
    isAuthenticated,
    isLoading,
    persona,
    profilePersona,
    setPersona,
    source,
    user,
  ]);

  if (isLoading || !isAuthenticated || !user || profilePersona || isAutoSaving) {
    return null;
  }

  const skipReady = skipState?.userId === user.id;
  if (!skipReady || skipState.skipped) return null;

  const isSuppressedRoute = SUPPRESSED_ROUTES.some((route) =>
    router.pathname.startsWith(route),
  );
  if (isSuppressedRoute) return null;

  const onSkip = () => {
    writePersonaOnboardingSkipped(user.id);
    setSkipState({ userId: user.id, skipped: true });
  };

  return (
    <div
      aria-modal="true"
      role="dialog"
      className="fixed inset-0 z-[130] overflow-y-auto bg-ink/70 px-4 py-8"
    >
      <div
        className={`${CONTAINER} flex min-h-full items-center justify-center`}
      >
        <section className="w-full max-w-[760px] border-2 border-ink bg-paper p-[clamp(24px,4vw,44px)] text-ink shadow-[12px_12px_0_rgba(20,62,111,0.22)]">
          <div className="mb-[28px] flex items-start justify-between gap-4">
            <div>
              <p className="text-[13px] font-extrabold uppercase tracking-[0.16em] text-brand">
                First-time setup
              </p>
              <p className="mt-[8px] max-w-[56ch] text-[15px] leading-[24px] text-ink/72">
                Choose the seat you are sitting in so Quizwerk can tune your
                dashboard, language, and starting points.
              </p>
            </div>
            <button
              type="button"
              onClick={onSkip}
              className="text-[14px] font-extrabold text-ink/70 underline-offset-4 hover:text-ink hover:underline"
            >
              Skip
            </button>
          </div>

          <PersonaPicker
            heading="Pick your Quizwerk persona"
            initialCategory={persona?.category ?? null}
            source="onboarding"
            onPicked={onSkip}
          />

          <div className="mt-[28px] border-t-2 border-divider pt-[18px]">
            <button type="button" onClick={onSkip} className={BTN_GHOST}>
              I&apos;ll do this later
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
