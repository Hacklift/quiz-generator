/**
 * Shared typography class for Quizwerk surfaces.
 *
 * Keep the same interface as a `next/font` instance so callers do not need to
 * know how the font stack is supplied. Using Tailwind's system sans stack
 * keeps production builds independent of Google Fonts network availability.
 */
export const archivo = { className: "font-sans" } as const;
