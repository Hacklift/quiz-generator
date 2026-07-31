import { parsePersona, type Persona } from "@shared/config/persona";
import type { PersonaSource } from "@features/persona/types/persona";

export interface ResolvePersonaInput {
  /** Persona stored on the signed-in user's profile. */
  profile: { category?: string | null; userType?: string | null } | null;
  /** ?persona= and ?category= from the current URL. */
  query: { persona?: string | null; category?: string | null };
  /** Guest choice from local storage. */
  stored: Persona | null;
}

export interface ResolvedPersona {
  persona: Persona | null;
  source: PersonaSource;
}

/**
 * Single resolution rule for the whole app: the signed-in profile wins,
 * then an explicit link, then a remembered guest choice.
 *
 * Pure by design — everything persona-aware depends on this, so it must be
 * trivially testable.
 */
export function resolvePersona({
  profile,
  query,
  stored,
}: ResolvePersonaInput): ResolvedPersona {
  const fromProfile = profile
    ? parsePersona(profile.category, profile.userType)
    : null;
  if (fromProfile) return { persona: fromProfile, source: "profile" };

  const fromQuery = parsePersona(query.category, query.persona);
  if (fromQuery) return { persona: fromQuery, source: "query" };

  if (stored) return { persona: stored, source: "storage" };

  return { persona: null, source: "none" };
}
