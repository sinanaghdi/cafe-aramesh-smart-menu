# Café Aramesh Smart Menu — Roadmap

A phase is complete only after acceptance criteria and tests pass, a report is provided, and the owner approves moving on.

## Phase 0 — Foundation
Plan and stack decisions, app scaffolds, Docker Compose, PostgreSQL schema/migration, Persian seed data, health checks, CI, contribution guidance, and architecture/API/AI documentation.

## Phase 1 — Customer menu and staff confirmation
Real category/product API, QR table context, anonymous session, cart validation, short-lived verification code, state machine, staff-only operational queue, audit events, live updates. No payment.

## Phase 2 — Study/work mode and club
Merchant-configurable study rules, mock Wi-Fi adapter and timed vouchers after staff confirmation, consent-based optional mobile club, mock OTP provider, points ledger, tiers/rewards, account deletion.

## Phase 3 — Smart combo and Persian NLP
Testable combo scoring for BOOST_BESTSELLER and PUSH_SLOW_MOVER; deterministic Persian synonym/tag search; optional AI provider; clarification for ambiguous queries; anonymized unanswered-query signals; merchant approval before publication.

## Phase 4 — Merchant management and insights
Menu/combo management, merchant-only analytics based on persisted data, Jalali period selection, CSV export, rule-based fallback insights, AI suggestions with evidence/confidence and explicit approve/reject.

## Phase 5 — Hardening and deployment readiness
Security and authorization review, IDOR and abuse tests, accessible responsive UI, performance checks, Playwright critical-flow coverage, structured logs, deployment docs, and 70%+ domain logic coverage.

## Future extensions — architecture only
These are not MVP features and must not be implemented within the phases above:
- Online ordering, if later validated by the business.
- A general AI agent.
- An AI customer-support assistant.

Keep possible extension points and feature flags documented; do not ship placeholder controls implying these features work.

## Release gate
The whole MVP is complete only when Compose starts and seeds the stack; customer-to-staff confirmation and eligible study vouchers work end to end; merchant analytics use persisted data; human approval is enforced; and CI/security/E2E checks are green.
