const SKIP_PREFIX = "quizwerk.personaOnboarding.skipped";

function keyFor(userId: string): string {
  return `${SKIP_PREFIX}.${userId}`;
}

export function readPersonaOnboardingSkipped(userId: string): boolean {
  if (typeof window === "undefined") return false;

  try {
    return window.localStorage.getItem(keyFor(userId)) === "true";
  } catch {
    return false;
  }
}

export function writePersonaOnboardingSkipped(userId: string): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(keyFor(userId), "true");
  } catch {
    // Losing this preference only means the user may see onboarding again.
  }
}
