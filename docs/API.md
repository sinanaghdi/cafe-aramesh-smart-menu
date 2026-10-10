# API contract and implementation status

This is a contract guide, not a claim that every endpoint is already implemented. Phase 0 implements only liveness and readiness. Implement planned endpoints only in their assigned phase and update this document in the same PR.

## Implemented in Phase 0
| Method | Path | Purpose |
|---|---|---|
| GET | /health | Liveness probe; no downstream dependency check. |
| GET | /ready | Readiness probe; checks PostgreSQL. |

## Planned API by phase

### Customer — Phase 1
- GET /api/v1/menu?table=... — published categories/products and verified table context.
- GET /api/v1/products/{product_id} — product details and structured attributes.
- POST /api/v1/orders — server validates menu prices and availability; creates a pending request only.
- GET /api/v1/orders/{public_id} — customer-safe order status; never reveal a confirmation secret.
- POST /api/v1/orders/{public_id}/verify — staff submits the customer's short code.
- GET /api/v1/staff/orders — staff-scoped operational queue only.
- PATCH /api/v1/staff/orders/{order_id}/status — legal state transitions only.
- GET /api/v1/staff/events — SSE stream when implemented.

### Study mode and loyalty — Phase 2
- GET/PUT /api/v1/merchant/study-mode-rules
- POST /api/v1/study-sessions and GET /api/v1/study-sessions/{session_id}
- POST /api/v1/club/otp/request and POST /api/v1/club/otp/verify
- GET /api/v1/club/account and POST /api/v1/club/account/delete

### NLP and combos — Phase 3
- POST /api/v1/menu/search — ranked existing products with explanation or clarification.
- GET /api/v1/menu/combos — approved, currently valid combos only.
- Merchant-only draft/approve/reject combo endpoints.
- GET /api/v1/merchant/nlp/unanswered — anonymized queries.

### Merchant — Phase 4
- Merchant-only category/product/combo/rule management.
- GET /api/v1/merchant/analytics?from=...&to=... and GET /api/v1/merchant/analytics/export.csv
- GET /api/v1/merchant/insights
- POST /api/v1/merchant/insights/{id}/decision — explicit approve/reject.

## Security invariants
- Staff endpoints must not include revenue, sales KPI, insight, or analytics fields even in API schemas.
- Server-calculated prices are authoritative; clients cannot set prices or discounts.
- Unknown table context, cross-cafe IDs, expired/replayed codes, throttled attempts, and illegal transitions fail closed.
- Use consistent error schemas and avoid returning secrets or personal data.
