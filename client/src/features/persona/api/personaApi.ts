import { api } from "@shared/api/http";
import type { Persona } from "@shared/config/persona";

/** Persists only persona fields; this is available to authenticated users. */
export async function updatePersona(persona: Persona) {
  const response = await api.put("/auth/profile/persona", {
    persona_category: persona.category,
    persona_user_type: persona.userType,
  });
  return response.data;
}
