# Architecture

## Phase 0 topology

    Browser
       |
    React + Vite
       |
    Nginx (static assets and /api proxy)
       |
    FastAPI API ---- PostgreSQL
       |
    Redis (optional supporting service)

The UI and API are separate deployable processes. PostgreSQL is the source of truth. Redis may support throttling or event fan-out but is not the only store for any business-critical state.

## Backend boundaries
- app/main.py: API entry point and liveness/readiness endpoints.
- app/core: environment-backed settings.
- app/db: SQLAlchemy metadata, sessions, and idempotent development seed.
- app/models: persisted domain entities.
- app/services: domain logic added during later feature phases.
- tests: unit/API tests; third-party services should be mocked.

Keep request/response schemas separate from database models when write endpoints are introduced. Routes should delegate transitions, code generation, recommendations, and analytics to independently testable services.

## Roles and authorization
Customer access is anonymous by default and scoped to a cafe and table/session. Staff can read and operate orders but must never receive merchant analytics endpoints or aggregate sales fields. Merchant users manage their own cafe and view its analytics. Enforce role and cafe scoping server-side; hiding controls is not authorization.

## Tenant isolation
Cafe-owned rows have cafe_id. Every read, write, event stream, background job, cache key, and export must be scoped to the authorized cafe. Do not trust a client-supplied cafe_id as proof of permission.

## Orders and human confirmation
The later order service owns transitions: DRAFT, PENDING_CONFIRMATION, CONFIRMED, PREPARING, SERVED, with terminal CANCELLED and EXPIRED states. Illegal transitions fail atomically. A client request is not a confirmed order, and this product does not process payments.

Confirmation codes must use a CSPRNG, be stored as a digest rather than plaintext, expire quickly, be single-use, be unique across active orders within a cafe, and be protected by attempt throttles. Consume codes atomically in a database transaction.

## Time and money
Store instants in timezone-aware UTC columns. Convert to Persian/Jalali and Asia/Tehran presentation at the UI/API boundary. Monetary values are integers with an explicit cafe unit (IRT/toman or IRR/rial).

## Migrations
Alembic owns schema evolution. The initial bootstrap migration creates the metadata declared in app/models; subsequent migrations must be explicit reviewed diffs and must not edit an already-applied migration. Demo data is seeded separately from schema migrations.

## Integration boundaries
- AIProvider: optional completion/embedding interface; rule-based behavior is always available.
- SmsProvider: mock/console implementation first.
- WifiAdapter: mock voucher adapter first; router integration later.
- SSE: add for the staff order queue after ordinary order APIs are correct.
- Online ordering, AI agent, and AI support stay architecture-only until separately approved.
