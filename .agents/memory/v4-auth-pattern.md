---
name: V4 auth pattern
description: Activation code + 2FA flow added in V4; new pages bypass generated hooks
---

## Activation code on register
- First user ever (user count = 0) is exempt — no code needed
- All subsequent users require a valid `activation_code` in POST /api/v1/auth/register
- Codes live in `activation_codes` table; marked `is_used=TRUE + used_by + used_at` after use
- Error detail strings: `activation_code_required`, `invalid_activation_code`, `activation_code_already_used`, `activation_code_expired`

## 2FA login flow
1. POST /auth/login → if `two_fa_enabled=TRUE` on user, return `{"requires_2fa": true, "email": "..."}` (no cookie set)
2. Frontend shows TOTP or email OTP tab UI
3. POST /auth/verify-2fa with `{email, code, method: "totp"|"email"}` → validates and sets JWT cookie

**Why:** Securely gates login without a temp-token complexity; email OTP uses account_vault.email_code_hash (SHA-256)

## New V4 pages use raw fetch
- No codegen run for new V4 endpoints (vault, gas, ai, profile, activation, referrals, wallet)
- Pages call `fetch("/api/v1/...", { credentials: "include" })` directly
- Only existing pre-V4 endpoints use generated hooks from @workspace/api-client-react
