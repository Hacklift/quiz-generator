import { api } from "@shared/api/http";
import type { Persona } from "@shared/config/persona";
import type { PersonaWriteSource } from "@features/persona/types/persona";

/** Persists persona onto the user profile without unlocking full profile edits. */
export async function updatePersona(
  persona: Persona,
  source: PersonaWriteSource = "profile",
) {
  const response = await api.put("/auth/profile/persona", {
    persona_category: persona.category,
    persona_user_type: persona.userType,
    source,
  });
  return response.data;
}
