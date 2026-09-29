"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
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

interface PersonaOverride {
  persona: Persona;
  userId: string | null;
}

export function PersonaProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading, refreshUser } = useAuth();
  const router = useRouter();

  // A successful profile write can take one render to reach AuthProvider.
  // Bind the optimistic value to that user so it cannot mask another
  // account's profile during an account switch in the same browser.
  const [override, setOverride] = useState<PersonaOverride | null>(null);
  const [storedPersona, setStoredPersona] = useState<Persona | null>(null);
  const [storageHydrated, setStorageHydrated] = useState(false);
  const wasAuthenticatedRef = useRef(isAuthenticated);

  useEffect(() => {
    setStoredPersona(readStoredPersona());
    setStorageHydrated(true);
  }, []);

  useEffect(() => {
    if (wasAuthenticatedRef.current && !isAuthenticated) {
      setOverride(null);
      setStoredPersona(null);
      clearStoredPersona();
    } else if (!wasAuthenticatedRef.current && isAuthenticated) {
      setOverride(null);
    }
    wasAuthenticatedRef.current = isAuthenticated;
  }, [isAuthenticated]);

  const resolved = useMemo(() => {
    if (override?.userId === (user?.id ?? null)) {
      return { persona: override.persona, source: "profile" as const };
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

    const hasTopicParam = typeof topic === "string";
    const normalizedTopic = hasTopicParam ? topic.trim().slice(0, 300) : "";
    const storedTopic = readStoredPersonaTopic(resolved.persona) || "";
    const storagePersona = storedPersona ?? readStoredPersona();
    const isStoredPersonaCurrent = samePersona(storagePersona, resolved.persona);
    const targetTopic = hasTopicParam ? normalizedTopic : storedTopic;

    if (!isStoredPersonaCurrent || storedTopic !== targetTopic) {
      writeStoredPersona(
        resolved.persona,
        hasTopicParam ? { topic } : undefined,
      );
    }
    if (!samePersona(storedPersona, resolved.persona)) {
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
        const userId = user?.id ?? null;
        setOverride({ persona, userId });
        try {
          await updatePersona(persona, options.source ?? "profile");
          await refreshUser();
          clearStoredPersona();
          setStoredPersona(null);
        } catch (error) {
          setOverride((current) =>
            current?.userId === userId ? null : current,
          );
          throw error;
        }
        return;
      }

      writeStoredPersona(persona);
      setStoredPersona(persona);
    },
    [isAuthenticated, refreshUser, user?.id],
  );

  const clearPersona = useCallback(() => {
    setOverride(null);
    setStoredPersona(null);
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
      isLoading: isLoading || !storageHydrated,
      setPersona,
      clearPersona,
    };
  }, [resolved, isLoading, storageHydrated, setPersona, clearPersona]);

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
