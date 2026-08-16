---
name: code-review-and-refactor
description: Workflow for reviewing pull requests, auditing code changes against security standards (ENGINEERING_REVIEW.md), and refactoring large files.
---

# Code Review and Refactor Skill

Use this workflow to review pull requests, audit security boundaries, or refactor existing components and modules.

## 1. Security & Quality Audit Checklist 

Review code changes against criteria from [`ENGINEERING_REVIEW.md`](../../../ENGINEERING_REVIEW.md):

### 🛡️ Authentication & Authorization
- [ ] Are protected routes secured with `Depends(get_current_user)`?
- [ ] Are sensitive token endpoints (`/auth/verify-otp`, `/auth/verify-link`) taking parameters in POST JSON bodies rather than query params?
- [ ] Are OTP verification checks using cryptographic functions (`secrets.randbelow`, `hmac.compare_digest`)?
- [ ] Does every private-data endpoint scope queries or ownership checks to `current_user.id`? (`get_current_user` returns a `UserOut` model, not a dictionary.)
- [ ] Do anonymous `/share` responses omit `correct_answer` and other answer data, as enforced by `server/app/share/services.py` and the share response schemas?

### ⚡ Performance & Efficiency
- [ ] Are unauthenticated or heavy AI endpoints guarded with per-IP rate limits (`@limiter.limit(...)`)?
- [ ] Are MongoDB queries using targeted projection fields and indexed keys?
- [ ] Is database write load minimized (avoiding redundant DB writes on every request)?

### 🎨 Frontend Quality & Accessibility
- [ ] Are components modular and split appropriately (avoiding 1,000+ line monolithic components)?
- [ ] Are proper `aria-*` attributes and focus management used in modals and interactive elements?
- [ ] Are API calls using route constants from `ROUTES` rather than hardcoded string literals?

---

## 2. Safe Refactoring Guidelines

1. **Preserve API Contracts**: Never alter existing route paths, query parameters, or JSON response shapes without updating all consumer sites in `client/` and backend tests.
2. **Preserve Existing Tests**: Run `pytest` and `pnpm test` before and after refactoring to ensure zero regressions.
3. **Incremental Component Extraction**: When refactoring oversized pages or components, extract sub-components into `components/` under `client/src/features/<feature>/`.
