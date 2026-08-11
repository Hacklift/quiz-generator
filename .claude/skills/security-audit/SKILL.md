---
name: security-audit
description: Checklist and workflow for auditing code changes against security standards, auth rules, and ENGINEERING_REVIEW.md findings.
---

# Security Audit Skill

Use this workflow to review pull requests or code edits for security risks before merging.

## 1. Security Verification Checklist

### 🔑 Authentication & Session Boundaries
- [ ] Are protected routes secured with `Depends(get_current_user)`?
- [ ] Are sensitive token endpoints (`/auth/verify-otp`, `/auth/verify-link`) taking parameters in POST JSON bodies rather than query params?
- [ ] Are OTP verification checks using cryptographic functions (`secrets.randbelow`, `hmac.compare_digest`)?
- [ ] Are password reset paths protected against brute-force attempts with rate limits and attempt counters?

### 🛡️ Authorization & Data Privacy
- [ ] Does the endpoint verify resource ownership (`user_id == current_user["id"]`) before returning or updating data?
- [ ] Are `/share` endpoints checking an explicit `is_shared` or `share_token` flag before revealing quiz contents?
- [ ] Are correct answers hidden from unauthenticated/shared quiz endpoints until submission?
- [ ] Are raw MongoDB `ObjectId` objects converted to strings and stripped of sensitive internal metadata?

### ⚡ Rate Limiting & Denial-of-Service (DoS)
- [ ] Are unauthenticated or AI-generation endpoints (`/api/get-questions`, `/share/share-email`) guarded with strict per-IP rate limits (`@limiter.limit(...)`)?
- [ ] Is file upload size checked incrementally or via `Content-Length` before buffering full payloads into memory?

### 🌐 Headers & CORS
- [ ] Is `client/next.config.mjs` retaining strong CSP headers (`frame-ancestors 'none'`, `X-Frame-Options DENY`, `Strict-Transport-Security`)?
- [ ] Are CORS origins restricted to validated environment hosts (avoiding `allow_origins=["*"]`)?

---

## 2. High-Priority Reference Check

Always cross-reference proposed architectural changes against [`ENGINEERING_REVIEW.md`](file:///c:/Users/hp/Desktop/Hacklift/quiz-generator/ENGINEERING_REVIEW.md) to ensure new features do not re-introduce P0 or P1 security vulnerabilities.
