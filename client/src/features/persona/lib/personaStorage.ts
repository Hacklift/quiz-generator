import { parsePersona, type Persona } from "@shared/config/persona";

/**
 * Guest persona storage.
 *
 * localStorage (not sessionStorage like TokenService): a visitor who picks
 * "Teacher" on the home page should still be a teacher tomorrow. Tokens use
 * sessionStorage for security reasons that don't apply to a display
 * preference.
 */
const STORAGE_KEY = "quizwerk.persona";
const STORAGE_VERSION = 1;

export function readStoredPersona(): Persona | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as {
      category?: string;
      userType?: string;
      v?: number;
    };
    if (parsed?.v !== STORAGE_VERSION) return null;

    return parsePersona(parsed.category, parsed.userType);
  } catch {
    // Corrupt or unavailable storage should never break rendering.
    return null;
  }
}

export function writeStoredPersona(persona: Persona): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...persona, v: STORAGE_VERSION }),
    );
  } catch {
    // Private browsing / quota — a lost preference is acceptable.
  }
}

export function clearStoredPersona(): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore.
  }
}
