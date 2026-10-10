# Local infrastructure

The root docker-compose.yml is the canonical local environment. It runs PostgreSQL, Redis, FastAPI, and the compiled React app behind Nginx.

Development-only defaults are intentionally convenient but must never be reused in production. Production deployment needs managed secrets, TLS, restrictive CORS, backups, monitoring, migration review, and an explicit data retention/deletion policy.

Redis is a supporting service. A future implementation must not rely on it for the only copy of an order, code consumption, or loyalty transaction.
