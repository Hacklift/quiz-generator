"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/router";
import { useAuth } from "@features/auth/context/authContext";
import {
  getCategoryDefinition,
  getUserTypeDefinition,
  type Persona,
} from "@shared/config/persona";
import { updatePersona } from "@features/persona/api/personaApi";
import {
  clearStoredPersona,
  readStoredPersona,
  readStoredPersonaTopic,
  writeStoredPersona,
} from "@features/persona/lib/personaStorage";
import { resolvePersona } from "@features/persona/lib/resolvePersona";
import type {
  PersonaState,
  PersonaWriteSource,
} from "@features/persona/types/persona";

const EMPTY_STATE: PersonaState = {
  persona: null,
  category: null,
  userType: null,
  definition: null,
  categoryDefinition: null,
  source: "none",
  isLoading: false,
  setPersona: async () => {},
  clearPersona: () => {},
};

const PersonaContext = createContext<PersonaState>(EMPTY_STATE);

const samePersona = (first: Persona | null, second: Persona | null) =>
  first?.category === second?.category && first?.userType === second?.userType;

export function PersonaProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading, refreshUser } = useAuth();
  const router = useRouter();

  // Local override so a fresh pick renders immediately, before the profile
  // round-trip completes.
  const [override, setOverride] = useState<Persona | null>(null);
  const [storedPersona, setStoredPersona] = useState<Persona | null>(null);

  useEffect(() => {
    setStoredPersona(readStoredPersona());
  }, []);

  useEffect(() => {
    if (!isAuthenticated && override && !storedPersona) {
      setOverride(null);
    }
  }, [isAuthenticated, override, storedPersona]);

  const resolved = useMemo(() => {
    if (override) {
      return { persona: override, source: "profile" as const };
    }
    return resolvePersona({
      profile: user
        ? {
            category: user.persona_category,
            userType: user.persona_user_type,
          }
        : null,
      query: {
        persona: (router.query?.persona as string) ?? null,
        category: (router.query?.category as string) ?? null,
      },
      stored: storedPersona,
    });
  }, [override, storedPersona, user, router.query]);

  useEffect(() => {
    if (resolved.source !== "query" || !resolved.persona) {
      return;
    }

    const topic = Array.isArray(router.query?.topic)
      ? router.query.topic[0]
      : router.query?.topic;

    const normalizedTopic =
      typeof topic === "string" ? topic.trim().slice(0, 300) : "";
    const storedTopic = readStoredPersonaTopic(resolved.persona) || "";
    const isStoredPersonaCurrent = samePersona(storedPersona, resolved.persona);

    if (!isStoredPersonaCurrent || storedTopic !== normalizedTopic) {
      writeStoredPersona(resolved.persona, { topic });
    }
    if (!isStoredPersonaCurrent) {
      setStoredPersona(resolved.persona);
    }
  }, [
    resolved.persona,
    resolved.source,
    router.query?.topic,
    storedPersona,
  ]);

  const setPersona = useCallback(
    async (
      persona: Persona,
      options: { source?: PersonaWriteSource } = {},
    ) => {
      if (isAuthenticated) {
        setOverride(persona);
        try {
          await updatePersona(persona, options.source ?? "profile");
          await refreshUser();
          if ((options.source ?? "profile") !== "inferred") {
            clearStoredPersona();
            setStoredPersona(null);
          }
        } catch (error) {
          setOverride(null);
          throw error;
        }
        return;
      }

      writeStoredPersona(persona);
      setStoredPersona(persona);
      setOverride(persona);
    },
    [isAuthenticated, refreshUser],
  );

  const clearPersona = useCallback(() => {
    setOverride(null);
    clearStoredPersona();
  }, []);

  const value = useMemo<PersonaState>(() => {
    const persona = resolved.persona;
    return {
      persona,
      category: persona?.category ?? null,
      userType: persona?.userType ?? null,
      definition: persona ? getUserTypeDefinition(persona.userType) : null,
      categoryDefinition: persona
        ? getCategoryDefinition(persona.category)
        : null,
      source: resolved.source,
      isLoading,
      setPersona,
      clearPersona,
    };
  }, [resolved, isLoading, setPersona, clearPersona]);

  return (
    <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>
  );
}

/**
 * Returns a safe "no persona" state outside a provider rather than throwing,
 * so persona-aware components can be rendered in isolation (and in tests)
 * without a wrapper.
 */
export function usePersona(): PersonaState {
  return useContext(PersonaContext);
}
