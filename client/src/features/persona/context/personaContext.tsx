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
  writeStoredPersona,
} from "@features/persona/lib/personaStorage";
import { resolvePersona } from "@features/persona/lib/resolvePersona";
import type { PersonaState } from "@features/persona/types/persona";

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

export function PersonaProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading, refreshUser } = useAuth();
  const router = useRouter();

  // Storage is hydrated only after the initial client render. Reading it in
  // render would make SSR see no persona while the browser sees one, causing
  // a hydration mismatch in persona-aware shell copy.
  const [storedPersona, setStoredPersona] = useState<Persona | null>(null);
  const [storageHydrated, setStorageHydrated] = useState(false);
  const [hasAuthenticatedSession, setHasAuthenticatedSession] = useState(false);

  useEffect(() => {
    setStoredPersona(readStoredPersona());
    setStorageHydrated(true);
  }, []);

  useEffect(() => {
    if (isLoading) return;

    if (isAuthenticated) {
      setHasAuthenticatedSession(true);
      return;
    }

    // A browser can be shared. Never allow a guest preference that survived
    // an authenticated session to become a later account's fallback persona.
    if (hasAuthenticatedSession) {
      clearStoredPersona();
      setStoredPersona(null);
      setHasAuthenticatedSession(false);
    }
  }, [hasAuthenticatedSession, isAuthenticated, isLoading]);

  const resolved = useMemo(() => {
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
      // Profile and explicit links remain available to signed-in users. Guest
      // storage is intentionally never an authenticated fallback.
      stored: isAuthenticated || hasAuthenticatedSession ? null : storedPersona,
    });
  }, [hasAuthenticatedSession, isAuthenticated, router.query, storedPersona, user]);

  const setPersona = useCallback(
    async (persona: Persona) => {
      if (isAuthenticated) {
        await updatePersona(persona);
        await refreshUser();
        // A profile save is authoritative. Remove the guest copy so it
        // cannot surface for another account on a shared browser.
        clearStoredPersona();
        setStoredPersona(null);
        return;
      }

      writeStoredPersona(persona);
      setStoredPersona(persona);
    },
    [isAuthenticated, refreshUser],
  );

  const clearPersona = useCallback(() => {
    clearStoredPersona();
    setStoredPersona(null);
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
