# Implementation status

## Implemented MVP workflows

- Persian RTL customer menu, category browsing, product search and rule-based preference discovery.
- FastAPI API with SQLAlchemy relational models for categories, products, combinations, users, tables, order snapshots, event history, work sessions, loyalty balances and settings.
- Development seed data and role-specific local demo accounts; no demo order history.
- Customer registration/login, password hashing, expiring JWT sessions and server-side role checks.
- Guest order requests with a four-digit confirmation secret, hashed verification value, 15-minute expiry, five-attempt cap, idempotency key, server-calculated prices and immutable line-item snapshots.
- Waiter queue, staff-only verification and guarded order transitions.
- Owner-only management APIs for categories, products, combos, work-mode settings and loyalty settings.
- Work-session eligibility checks and server-side expiration state; no unsupported Wi-Fi integration is claimed.
- Loyalty ledger and non-negative conditional balance updates for redemption.
- Daily/weekly/monthly completed-order reports and rule-based business insights that disclose insufficient data.
- Alembic migration scaffold, GitHub Actions test workflow, deployment documentation and static GitHub Pages workflow.

## Constraints that remain

- The rule-based preference engine is not an LLM. No paid AI provider is configured.
- The MVP does not process payments or reconcile with a POS; recorded order values are not the café's full accounting revenue.
- Work Mode records timed eligibility and instructions but does not connect to a router or revoke Wi-Fi access.
- Loyalty reward redemption records a request for staff review; it does not apply a cash-register discount automatically.
- The starter version does not include SMS/email verification or password reset delivery.
- Production readiness still requires service-specific deployment configuration, HTTPS, monitoring, backups, managed database operations, rate limiting and security review.
- The GitHub Pages site can display the frontend only. Real ordering and authenticated panels require a deployed API and database configured in `config.js`.
- Full browser screenshot QA is not automatically asserted by the test suite.
