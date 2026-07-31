import { api } from "@shared/api/http";
import type { Persona } from "@shared/config/persona";

/** Persists persona onto the user profile (rides PUT /auth/profile). */
export async function updatePersona(persona: Persona) {
  const response = await api.put("/auth/profile", {
    persona_category: persona.category,
    persona_user_type: persona.userType,
  });
  return response.data;
}
