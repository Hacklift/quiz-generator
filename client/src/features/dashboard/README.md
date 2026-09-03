# Dashboard feature

`/dashboard` resolves the user's persona, dispatches to a **category**
dashboard, which dispatches to a **user-type** view.

```
pages/DashboardPage.tsx        [SCAFFOLD-OWNED]  auth + persona gate + category dispatch
  school/SchoolDashboard.tsx   #124 (done)       category chrome + user-type dispatch map
    school/views/*.tsx         one ticket each   #126 #127 #128 #129
  corporate/CorporateDashboard.tsx  #125 (done)  category chrome + user-type dispatch map
    corporate/views/*.tsx      one ticket each   #130 #131 #132
components/                    [SCAFFOLD-OWNED]  DashboardShell, QuickActions,
                                                 RecentQuizzes, DashboardPlaceholder,
                                                 PersonaGate
types/dashboard.ts             [SCAFFOLD-OWNED]  DashboardViewProps
```

## Filling in a stub

Your view is rendered **inside** `<DashboardShell>` by its category
dashboard, so render sections — not page chrome, not a NavBar.

```tsx
export default function TeacherDashboard({ persona, user }: DashboardViewProps) {
  const t = useTerms();
  return (
    <section className="border-t-2 border-divider pt-[28px]">
      <h2 className="text-[20px] font-extrabold tracking-[-0.015em]">
        Your {t("group", "plural")}
      </h2>
      …
    </section>
  );
}
```

Rules:

- **Terminology via `useTerms()`.** Never write "students" or "team" directly —
  the same component serves several personas.
- **Styling via `@shared/ui/quizwerk`.** `BTN_PRIMARY`, `BTN_GHOST`, `CONTAINER`,
  `Kicker`, `Microlabel`. Zero border-radius, flush left, 2px rules.
- **Only touch your own file.** `[SCAFFOLD-OWNED]` files are shared by every
  dashboard ticket; if you need a change there, raise it in your PR rather than
  making it.
- **Add your own test** as `client/__tests__/<YourView>.test.tsx` — the shared
  `DashboardPage.test.tsx` only asserts that dispatch reaches you.
- **Destructure only the props you use.** CI runs `next build`, whose lint pass
  fails on an unused binding.

## Why static imports

Both dispatch maps import every view eagerly. That is deliberate: `next build`
then fails immediately if a view file is missing or misnamed, and jest needs no
async plumbing. Do not switch them to `next/dynamic`.
