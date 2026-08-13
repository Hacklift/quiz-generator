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
const MAX_STORED_TOPIC_LENGTH = 300;

export function readStoredPersona(): Persona | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as {
      category?: string;
      userType?: string;
      topic?: string;
      v?: number;
    };
    if (parsed?.v !== STORAGE_VERSION) return null;

    return parsePersona(parsed.category, parsed.userType);
  } catch {
    // Corrupt or unavailable storage should never break rendering.
    return null;
  }
}

export function readStoredPersonaTopic(persona?: Persona | null): string | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw) as {
      category?: string;
      userType?: string;
      topic?: string;
      v?: number;
    };
    if (parsed?.v !== STORAGE_VERSION || typeof parsed.topic !== "string") {
      return null;
    }

    const storedPersona = parsePersona(parsed.category, parsed.userType);
    if (
      persona &&
      (!storedPersona ||
        storedPersona.category !== persona.category ||
        storedPersona.userType !== persona.userType)
    ) {
      return null;
    }

    const topic = parsed.topic.trim();
    return topic ? topic : null;
  } catch {
    return null;
  }
}

export function writeStoredPersona(
  persona: Persona,
  context: { topic?: string | null } = {},
): void {
  if (typeof window === "undefined") return;

  try {
    const existingPersona = readStoredPersona();
    const existingTopic = readStoredPersonaTopic(persona);
    const topic =
      typeof context.topic === "string"
        ? context.topic.trim().slice(0, MAX_STORED_TOPIC_LENGTH)
        : existingPersona?.category === persona.category &&
            existingPersona?.userType === persona.userType
          ? existingTopic || ""
          : "";
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        ...persona,
        ...(topic ? { topic } : {}),
        v: STORAGE_VERSION,
      }),
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
