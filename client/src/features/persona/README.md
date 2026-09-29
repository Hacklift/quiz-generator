# Persona feature

Who the user is — a **category** (`school` | `corporate`) and a **user type**
(`teacher` `lecturer` `student` `parent` | `business` `employee` `hr`).

## Reading persona

```tsx
const { persona, definition, category, userType, source } = usePersona();
```

`usePersona()` **never throws**, even outside `PersonaProvider` — it returns an
empty state. That is what lets a persona-aware component be rendered in a plain
`render()` without a wrapper.

Resolution order (`lib/resolvePersona.ts`, pure and unit-tested):

1. **profile** — the signed-in user's saved persona
2. **query** — `?persona=&category=` on the current URL
3. **storage** — a guest's earlier choice (`localStorage`, survives tab close;
   unlike `TokenService`, which uses `sessionStorage` for token security).
   It is hydrated after mount, never used as an authenticated fallback, and is
   cleared when an authenticated session ends on a shared browser.
4. **none**

An inconsistent pair (`?category=corporate&persona=teacher`) resolves to
nothing rather than guessing.

## Writing persona

```tsx
const { setPersona } = usePersona();
await setPersona({ category: "school", userType: "teacher" });
```

For guests this writes browser storage. For authenticated users it first saves
through `PUT /auth/profile/persona`, refreshes the profile, then removes any
guest storage copy. A failed profile save leaves both the profile and guest
storage unchanged.

## Wording

```tsx
const t = useTerms();
t("learner", "plural");   // "students" (school) · "team members" (corporate)
t("group");               // "class" · "team" · "cohort" for a lecturer
```

Keys live in `@shared/config/terminology.ts`, resolving user-type override →
category → neutral default. **Persona views must never hardcode these nouns.**

## Components

- `PersonaPicker` — two-step category → user-type picker. Used by the dashboard's
  unset state, onboarding (#120) and profile settings (#122). Don't fork it.
- `PersonaBadge` — the "Set up for: Teacher" chip.

## Changing the taxonomy

Slugs exist in two places and must change together in one PR:

- `client/src/shared/config/persona.ts` — slugs **and** all copy
- `server/app/users/persona.py` — slugs only, plus the `PersonaUserTypeField`
  literal in `server/app/users/models.py`

`server/tests/test_persona_taxonomy.py` fails if they drift. The Mongo validator
rejects unknown slugs, so **deploy the backend before shipping a frontend that
emits a new one**.
