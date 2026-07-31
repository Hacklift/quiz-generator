import type {
  Persona,
  PersonaCategory,
  PersonaCategoryDefinition,
  PersonaUserType,
  PersonaUserTypeDefinition,
} from "@shared/config/persona";

export type { Persona, PersonaCategory, PersonaUserType };

/** Where the active persona came from, most trusted first. */
export type PersonaSource = "profile" | "query" | "storage" | "none";

export interface PersonaState {
  persona: Persona | null;
  category: PersonaCategory | null;
  userType: PersonaUserType | null;
  definition: PersonaUserTypeDefinition | null;
  categoryDefinition: PersonaCategoryDefinition | null;
  source: PersonaSource;
  isLoading: boolean;
  /** Persists to the profile when signed in, otherwise to local storage. */
  setPersona: (persona: Persona) => Promise<void>;
  clearPersona: () => void;
}
