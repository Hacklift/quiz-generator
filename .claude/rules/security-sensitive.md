---
paths:
  - "server/app/auth/**"
  - "server/app/share/**"
  - "server/app/billing/**"
  - "server/app/quiz/routes/**"
---

# Security-sensitive paths

These directories handle auth, sharing, billing, or public-facing quiz data.
Apply these rules on every change here, not just during formal review.

## Tenancy & access control
- `get_current_user` returns `server.app.users.models.UserOut`; access it with attributes such as `current_user.id`, never dictionary subscripting.
- Every endpoint returning or mutating private user data must scope its query or ownership check to `current_user.id` before proceeding.
- Preserve the current public-sharing boundary: anonymous shared-quiz responses must omit `correct_answer` and other answer data. Do not assume an `is_shared` or `share_token` field exists; inspect `server/app/share/routes.py`, `server/app/share/services.py`, and the response schemas before changing sharing behavior.
- Never build outbound links or emails from client-supplied URLs; construct them server-side from validated IDs.

## Secrets & comparisons
- OTPs and tokens must use `secrets.randbelow` / `secrets.token_*` for generation, never `random`.
- Compare secrets with `hmac.compare_digest`, never `==` or `!=`.
- Verification credentials (OTP, tokens) go in POST JSON bodies, never query parameters.

## Rate limiting
- Any public or AI-generation-heavy endpoint needs `@limiter.limit(...)`. Don't rely on the global default.

## When in doubt
Check `ENGINEERING_REVIEW.md` for the specific finding this pattern relates to before assuming a shortcut is safe — several of these are P0 fixes for known issues, not just style preferences.
