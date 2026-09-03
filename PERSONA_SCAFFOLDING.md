# Persona work — where things live and who owns what

The app is moving from one generic experience to a **category** (School /
Corporate) and, inside it, a **user type** (teacher, lecturer, student, parent /
business, employee, HR). This document is the map for the 20 issues that
deliver it.

Scaffolding is done. Every ticket below is a self-contained edit — in most
cases a single file — against contracts that already exist and are tested.

---

## The shape of it

```
Sign-up / home page / profile
        │  persona chosen
        ▼
profile.persona {category, user_type}      ← server/app/users/persona.py
        │  flattened onto UserOut, so current_user carries it everywhere
        ▼
usePersona()                                ← features/persona/context
        │  profile > ?persona= > localStorage > none
        ├──► useTerms()   "students" vs "team members"
        └──► /dashboard   category dispatch → user-type view
```

## Files you can rely on

| File | What it gives you |
|---|---|
| `client/src/shared/config/persona.ts` | The taxonomy: `PersonaCategory`, `PersonaUserType`, `PERSONA_TAXONOMY`, `parsePersona`, `personaGenerateHref`, per-type `generationDefaults` |
| `server/app/users/persona.py` | The same slugs server-side, plus `build_persona` / `get_persona` / `persona_update_fields` |
| `client/src/shared/config/terminology.ts` | `resolveTerm(key, persona, form)` — category wording with user-type overrides |
| `client/src/features/persona/` | `usePersona()`, `useTerms()`, `PersonaPicker`, `PersonaBadge`, storage, API |
| `client/src/shared/ui/quizwerk/` | The design kit: `CONTAINER`, `BTN_PRIMARY`, `BTN_GHOST`, `BTN_INVERSE`, `Kicker`, `Microlabel`, `archivo` |
| `client/src/features/dashboard/` | `DashboardShell`, `QuickActions`, `RecentQuizzes`, `DashboardPlaceholder`, both dispatch maps |

## House rules

1. **Never hardcode a learner/class/team noun.** Call `t("learner", "plural")`
   from `useTerms()`. Add a key to `terminology.ts` if yours is missing.
2. **Never hand-roll a button or container.** Import from `@shared/ui/quizwerk`.
3. **Never edit a `[SCAFFOLD-OWNED]` file** in a view ticket — those are shared
   and changing one conflicts with eight other people. Raise it in your PR
   instead.
4. **Persona slugs change in both languages, same PR.**
   `server/tests/test_persona_taxonomy.py` fails otherwise.
5. `usePersona()` works without a provider (returns an empty state), so your
   view renders in a plain `render()` with no wrapper.

---

## Story → files you own

### Done (this scaffolding)

| Issue | Story | Landed as |
|---|---|---|
| #119 | Persona on the user profile | `server/app/users/{persona,models,repository,services,validators,identity}.py` |
| #123 | Terminology + nav shell | `shared/config/terminology.ts`, `features/quiz/components/{NavBar,Sidebar,Footer}.tsx` |
| #124 | School dashboard shell | `features/dashboard/school/SchoolDashboard.tsx` |
| #125 | Corporate dashboard shell | `features/dashboard/corporate/CorporateDashboard.tsx` |

### Ready to pick up

| Issue | Story | Files you own | Notes |
|---|---|---|---|
| #120 | Onboarding picker after signup | new `features/auth` wiring | `PersonaPicker` is built — you own where/when it appears and the show-once rule |
| #121 | Carry home persona through signup | `features/auth/components/SignUpModal.tsx` | Storage + query resolution already exist; carry the value across the auth hop |
| #122 | Edit persona in settings | `features/profile/pages/ProfilePage.tsx` | Drop in `PersonaPicker`, save via `updatePersona` |
| #126 | Teacher view | `features/dashboard/school/views/TeacherDashboard.tsx` | |
| #127 | Lecturer view | `features/dashboard/school/views/LecturerDashboard.tsx` | |
| #128 | Student view | `features/dashboard/school/views/StudentDashboard.tsx` | Blocked on #143 for scored history |
| #129 | Parent view | `features/dashboard/school/views/ParentDashboard.tsx` | |
| #130 | Business view | `features/dashboard/corporate/views/BusinessDashboard.tsx` | |
| #131 | Employee view | `features/dashboard/corporate/views/EmployeeDashboard.tsx` | |
| #132 | HR view | `features/dashboard/corporate/views/HrDashboard.tsx` | |
| #133 | Generation defaults | `features/quiz/components/QuizForm.tsx` | Consume `PERSONAS[type].generationDefaults` — do not re-derive |
| #134 | Template libraries | `server/app/quiz/services/category_seed_service.py`, category pages | |
| #135 | Class results export | new `server/app/quiz/routes/` endpoint + download UI | |
| #136 | Compliance reporting | new endpoint + HR view section | |
| #137 | Adoption analytics | `server/app/users/`, auth events | Indexes on `profile.persona.*` already exist |
| #143 | Attempt history with scores | new v2 collection + `/api/quiz-attempts` | Unblocks #128 and #131 |

---

## Adding a new user type

1. `client/src/shared/config/persona.ts` — add the slug to its category array
   and a full definition (label, description, sample topic, generation defaults).
2. `server/app/users/persona.py` — add the slug to
   `PERSONA_USER_TYPES_BY_CATEGORY`.
3. `server/app/users/models.py` — add it to the `PersonaUserTypeField` literal
   (it cannot be generated from the tuple).
4. Add a view file and register it in that category's dispatch map.
5. **Deploy the backend before the frontend can emit it** — the Mongo validator
   rejects unknown slugs.

## Open product questions

- **Is `/dashboard` the post-login landing?** The route exists; no redirect was
  changed. This decides whether later tickets are new pages or wrappers around
  `/profile`, `/saved_quiz`, `/quiz_history`.
- **Generation defaults** in `persona.ts` are engineering placeholders marked
  `TODO(#133)` — product should confirm audience, difficulty, length and format
  per user type.
- **Persona on the quiz document.** #136 and #137 will want persona on
  `quizzes_v2`, not just on the user. That is a v2-repository change with no
  story yet.
