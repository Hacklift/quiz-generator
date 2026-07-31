/**
 * Quizwerk design-system class strings (design_handoff_home_page).
 *
 * Rules of the visual language: zero border-radius, everything flush left,
 * 2px divider rules, Archivo 800 headings, navy spent sparingly.
 *
 * These strings are copied verbatim from the original home page. Do not
 * "tidy" them into Tailwind scale values — the arbitrary values are the spec.
 */

/** 1200px content column with the handoff's responsive padding. */
export const CONTAINER =
  "mx-auto w-full max-w-[1200px] px-[clamp(20px,5vw,72px)]";

/** 2px section seam. */
export const RULE = "border-t-2 border-divider";

export const BTN_BASE =
  "inline-flex min-h-[44px] cursor-pointer items-center justify-center whitespace-nowrap px-[16px] py-[10px] text-[14px] font-extrabold leading-[1.2] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand";

export const BTN_PRIMARY = `${BTN_BASE} bg-brand text-paper transition hover:bg-brand-600`;

export const BTN_GHOST = `${BTN_BASE} border-2 border-ink bg-transparent text-ink transition hover:bg-ink/[0.07]`;

/** Ghost button for use inside a navy field (paper border, paper text). */
export const BTN_INVERSE = `${BTN_BASE} border-2 border-paper text-paper transition hover:bg-paper/[0.12] focus-visible:outline-paper`;
