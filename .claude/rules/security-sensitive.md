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
- Every endpoint returning or mutating user data must verify `user_id == current_user["id"]` before proceeding.
- `/share` and any public-read endpoint must gate on an explicit `is_shared` / `share_token` flag before returning quiz content — including `correct_answer`.
- Never build outbound links or emails from client-supplied URLs; construct them server-side from validated IDs.

## Secrets & comparisons
- OTPs and tokens must use `secrets.randbelow` / `secrets.token_*` for generation, never `random`.
- Compare secrets with `hmac.compare_digest`, never `==` or `!=`.
- Verification credentials (OTP, tokens) go in POST JSON bodies, never query parameters.

## Rate limiting
- Any public or AI-generation-heavy endpoint needs `@limiter.limit(...)`. Don't rely on the global default.

## When in doubt
Check `ENGINEERING_REVIEW.md` for the specific finding this pattern relates to before assuming a shortcut is safe — several of these are P0 fixes for known issues, not just style preferences.