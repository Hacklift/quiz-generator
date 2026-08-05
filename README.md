# quiz-generator

Generate quizzes in a particular field.

## Running locally

The app is a Next.js client and a FastAPI server:

```bash
docker compose up
```

Client on http://localhost:3000, API on http://localhost:8000.

> **Note:** the legacy `streamlit run quiz.py` entry point at the repo root
> predates the current client/server split and is no longer how the app runs.

## Docs

- [PERSONA_SCAFFOLDING.md](PERSONA_SCAFFOLDING.md) — the persona programme:
  where the taxonomy lives, the shared seams, and which issue owns which file.
- [client/src/features/persona/README.md](client/src/features/persona/README.md)
  — reading and writing persona, terminology rules.
- [client/src/features/dashboard/README.md](client/src/features/dashboard/README.md)
  — how to fill in a persona dashboard view.
- [ENGINEERING_REVIEW.md](ENGINEERING_REVIEW.md) — 2026-07 review and what was
  actioned.
- [CLAUDE_PR_REVIEW.md](CLAUDE_PR_REVIEW.md) — how automated Claude PR reviews
  run, how to trigger them, and the required repository secret.
