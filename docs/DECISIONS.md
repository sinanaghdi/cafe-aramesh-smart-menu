# Architecture decision records

## ADR-001 — React + Vite instead of Next.js
**Status:** Accepted. **Date:** 2026-10-10.

The MVP's value is a Persian-first QR menu with a separately protected API; it does not require server-side rendering. React + Vite produces a small static frontend, simplifies deployment, and keeps the API boundary explicit. Reconsider only if a demonstrated SSR requirement appears.

## ADR-002 — FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
**Status:** Accepted. **Date:** 2026-10-10.

This stack provides typed API validation, explicit transactional domain services, relational constraints, and versioned migrations. PostgreSQL is the authoritative store; SQLite is not the production target.

## ADR-003 — Redis is optional
**Status:** Accepted. **Date:** 2026-10-10.

Redis may back throttling or event fan-out, but order correctness, code consumption, and loyalty transactions must remain correct in PostgreSQL.

## ADR-004 — No payment or POS
**Status:** Accepted. **Date:** 2026-10-10.

The system records requests and human confirmation, not payments or accounting sales. Displayed order values are not automatically equivalent to accounting revenue.

## ADR-005 — Human-in-the-loop recommendations
**Status:** Accepted. **Date:** 2026-10-10.

AI can suggest combos and business insights but cannot publish or apply them without explicit merchant action. Approval is checked server-side and audited.

## ADR-006 — Protect main
**Status:** Recommended, not changed. **Date:** 2026-10-10.

After CI is stable, enable branch rules requiring pull requests and successful CI (and an approval where practical). Repository protection is not changed without owner confirmation.
