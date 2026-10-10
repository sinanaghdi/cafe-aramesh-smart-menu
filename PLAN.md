# Implementation Plan — Café Aramesh Smart Menu

## Product goal
Replace a static cafe menu with a Persian-first, mobile-first menu that helps customers choose products while preserving deliberate in-person staff confirmation. This is not a POS, accounting system, inventory tool, or full CRM.

## Repository findings
- The default branch is main.
- The existing repository contained README.md, LICENSE, .gitignore, and the two product documents under docs/.
- No executable frontend/backend, database models, migrations, Docker Compose stack, tests, or CI workflow existed at planning time.
- Existing product boundaries and Persian RTL requirements are retained.

## Technical decisions
- Backend: Python 3.12, FastAPI, Pydantic v2 / pydantic-settings, SQLAlchemy 2, Alembic, PostgreSQL, psycopg 3.
- Frontend: React + Vite + TypeScript. The MVP does not need SSR; static frontend deployment keeps the API boundary simple.
- Styling: CSS design tokens in the scaffold; Persian RTL and mobile-first behavior are mandatory regardless of styling tool.
- Realtime: SSE for the staff queue unless implementation findings justify otherwise.
- Redis: optional for throttling/pub/sub; core domain correctness must not depend on it.
- AI: rule-based behavior is always available. External providers are optional and never receive customer PII.
- Money: integer amounts; each cafe declares IRR (rial) or IRT (toman). Seed prices use toman.
- Time: timezone-aware UTC timestamps in storage; Jalali formatting belongs in the UI.
- Multi-tenancy: each cafe-owned domain table carries cafe_id, and server-side queries enforce cafe scoping.

## Phased implementation
### Phase 0 — Foundation (current PR)
- [x] Inspect the repository and create this plan before feature work.
- [ ] Establish backend/frontend scaffolds and Docker Compose.
- [ ] Add SQLAlchemy domain models, initial Alembic migration, and idempotent Persian seed data (20–30 products).
- [ ] Add health/readiness endpoints and a smoke test.
- [ ] Add CI, Dependabot, issue/PR templates, Makefile, environment example, and bilingual instructions.
- [ ] Add architecture, API, AI, decisions, and forward roadmap documentation.
- [ ] Open a PR; do not merge or start Phase 1 before review/approval.

Acceptance: local Compose builds and starts web/API/PostgreSQL/Redis; API becomes healthy; migration and seed run; CI checks succeed; no real order flow or fake business analytics are claimed.

### Phase 1 — Customer menu, cart, verification code, and staff queue
Build the real menu API, QR table context, anonymous session, server-side cart validation, cryptographically random short confirmation code, expiry/rate limits, tested order state machine, audit events, staff-only operational queue, SSE, and customer-to-staff E2E. No payment.

### Phase 2 — Study/work mode and loyalty club
Add editable study rules, mock Wi-Fi adapter and timed vouchers after staff confirmation, opt-in mobile club, mock OTP provider, consent/deletion, points ledger, tiers, and rewards.

### Phase 3 — Persian NLP search and smart combos
Build deterministic Persian normalization/synonyms/tag matching, clarification for ambiguity, explainable combo scoring using sales velocity/margin/co-occurrence/time/cart, anonymized unanswered-query logs, and merchant approval before publication.

### Phase 4 — Merchant management, analytics, and AI insights
Add merchant-only menu/combo/rule management, date-range KPI calculations based on persisted events, Jalali period selection, CSV export, evidence-backed insights, and explicit approve/reject actions. Statistical fallback must work without AI.

### Phase 5 — Hardening and release readiness
Complete authz/IDOR/abuse controls, structured logs, accessibility, constrained-mobile performance, Playwright E2E, deployment docs, and at least 70% coverage for domain logic (state machine, code handling, combo ranking, NLP).

## Future extensions — architecture only
Online ordering, a general AI agent, and an AI support assistant are explicitly out of MVP scope. Keep extension points/interfaces and feature flags possible, but do not implement the features in these phases.

## Definition of done for the whole MVP
- docker compose up --build starts and seeds the stack.
- Customer scans a table QR, browses/searches, adds items, receives a short code, and asks staff to confirm in person.
- Only after confirmation can eligible study mode receive a voucher.
- Merchant sees data-backed analytics and explicitly approves/rejects recommendations.
- CI is green; docs match behavior; incomplete features are not represented as working.

## Phase gate
Only Phase 0 is in scope for this PR. Report checks, remaining work, and risks, then stop. Phase 1 requires explicit user approval.
