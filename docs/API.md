# API contract — Phase 1 implemented

All external URLs are proxied by Nginx with the `/api` prefix; FastAPI routes are mounted under `/v1`. The root GitHub Pages prototype is static only and does not call these routes.

## System
| Method | Backend path | Purpose |
|---|---|---|
| GET | /health | Liveness, independent of PostgreSQL |
| GET | /ready | Readiness; verifies PostgreSQL |
| GET | /docs | Interactive API docs in local development |

## Customer menu and requests
| Method | Backend path | Purpose |
|---|---|---|
| GET | /v1/menu?table=5 | Categories, available/featured products, structured tags and table context |
| POST | /v1/orders | Validate table, current product availability and prices; create a pending request; set anonymous HTTP-only session cookie |
| GET | /v1/orders/{id} | Read status only for the customer session that created the request |

POST /v1/orders expects a table number and 1–50 product/quantity lines. Prices and totals are computed from the database; client-supplied totals are ignored. The response contains the short confirmation code once. Only an HMAC digest is stored; the code expires after the configured duration and is single-use.

## Staff authentication
| Method | Backend path | Purpose |
|---|---|---|
| POST | /v1/auth/login | Password-hash verification; return short-lived access + refresh token |
| POST | /v1/auth/refresh | Rotate refresh session; replay of a revoked token is rejected |
| POST | /v1/auth/logout | Revoke the supplied refresh session |
| GET | /v1/staff/orders | Staff-only operations queue with optional status filter |
| GET | /v1/staff/events | Staff-only SSE snapshot stream |
| POST | /v1/staff/orders/{id}/confirm | Check the customer's code, expiry, state, and attempt limits |
| PATCH | /v1/staff/orders/{id}/status | Move confirmed/preparing orders forward or cancel with a reason |

Staff response schemas intentionally do not include total_amount, line prices, revenue, analytics, or merchant insights. Authorization and cafe scoping are checked at the API layer.

## Status machine
- `draft → pending_confirmation → confirmed → preparing → served`
- `draft` and `pending_confirmation` may be cancelled or expire.
- `confirmed` and `preparing` may be cancelled; cancellation requires a reason.
- `served`, `cancelled`, and `expired` are terminal.
- Confirmation to `confirmed` can happen only through code verification.

## Development demo login
The seed creates local-only demo accounts when ENVIRONMENT is not production:
- Staff: `staff@aramesh.local` / `StaffDemo!2026`
- Merchant: `merchant@aramesh.local` / `MerchantDemo!2026`

Set environment variables to override credentials before local use. These are not production credentials. Production seed deliberately skips demo users.

## Security notes
- Anonymous customer identity is a random HTTP-only cookie; orders store a SHA-256 digest of the session token, not the raw cookie.
- Confirmation codes are generated with Python's CSPRNG, HMACed with a secret, unique among active codes per cafe, expiring and single-use.
- Failed code attempts are persisted per order and lock the code at the configured limit; endpoint-level throttling uses Redis with a bounded development-only in-process fallback.
- JWT refresh tokens are tracked by hashed JTI and rotated/revoked in PostgreSQL.
- All user/order/item reads are scoped by cafe, and customer status reads are scoped by session digest.
- These endpoints do not take payment and do not turn a request into an accounting sale.


## Phase 2 — Study mode and loyalty

| Method | Path | Access |
|---|---|---|
| GET/PUT | /v1/merchant/study-rules | Merchant only |
| GET/PUT | /v1/merchant/loyalty-rules | Merchant only |
| POST | /v1/club/otp/request | Consent + rate limit |
| POST | /v1/club/otp/verify | Single-use OTP; sets HTTP-only club session |
| GET | /v1/club/account | Club session |
| POST | /v1/club/rewards/{id}/redeem | Club session + idempotency key |
| POST | /v1/club/account/delete | Club session; anonymizes account identity |

Study mode is requested in `POST /v1/orders` using `study_mode_requested` and `study_duration_minutes`. The reservation remains pending until the staff code check succeeds. Only then may the mock WifiAdapter issue a time-limited voucher. The customer order-status route exposes a voucher only for the same anonymous customer session that created the order.

The club OTP is HMAC-hashed in storage, expires after five minutes, and locks after five wrong attempts. `debug_code` is returned only when `ENVIRONMENT` is not production so local testing does not require a real SMS provider. The Console SMS adapter never logs the OTP code. A production SMS gateway is not implemented yet.
