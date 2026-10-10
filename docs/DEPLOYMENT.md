# Deployment guide / راهنمای استقرار

## 1. Local development

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually if `cp` is unavailable. The development defaults use SQLite at `backend/cafe_aramesh.db`.

```bash
alembic upgrade head
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

Open `http://127.0.0.1:8000`. API docs are at `/docs` and the health check is `/api/health`.

## 2. Development accounts

Only for local development; do not reuse these passwords in a public or production environment:

| Role | Email | Password |
|---|---|---|
| Owner | `owner@aramesh.local` | `Owner@12345` |
| Waiter | `waiter@aramesh.local` | `Waiter@12345` |
| Member | `member@aramesh.local` | `Member@12345` |

Sample menu data is created only outside production. No sample order history is seeded.

## 3. Environment settings

- `APP_ENV`: use `development` locally and `production` for a deployment.
- `DATABASE_URL`: SQLite locally; use a managed PostgreSQL URL for persistent hosted data.
- `JWT_SECRET`: generate a unique random string with at least 32 characters for production. Never commit it.
- `CAFE_TIMEZONE`: defaults to `Asia/Tehran`.
- `CORS_ORIGINS`: comma-separated exact origins when the static site and API are hosted separately.
- `AUTO_CREATE_SCHEMA`: leave false in production; apply migrations instead.

Generate a secret locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 4. Separate static hosting and API

GitHub Pages runs only static files. It cannot execute FastAPI or host a database. The site can remain on Pages while the API and PostgreSQL run on a server/platform.

1. Deploy the FastAPI app with `alembic upgrade head` and `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
2. Set `APP_ENV=production`, `JWT_SECRET`, `DATABASE_URL`, and an exact `CORS_ORIGINS` value on the API host.
3. Set `apiBaseUrl` in `config.js` to the API's HTTPS origin, for example `https://your-api.example.com`, then commit the public configuration change.
4. Keep secrets only in the hosting platform's environment settings.

The API also serves the current static site from its root when run as a single service. When separate static hosting is used, the browser calls the configured API origin.

## 5. Database migrations

For a fresh or upgraded database:

```bash
alembic upgrade head
```

Model changes should be made with new Alembic revisions. Back up the database before running migrations on live data.

## 6. Docker

```bash
docker build -t cafe-aramesh .
docker run --rm -p 8000:8000 --env-file .env cafe-aramesh
```

For production, use a managed PostgreSQL database or persistent storage. A container filesystem is not guaranteed to persist SQLite data across redeploys.

## 7. Test and quality commands

```bash
node --check app.js
python -m compileall -q backend migrations tests
pytest -q
alembic upgrade head
```

The GitHub Actions workflow runs JavaScript syntax validation, Python compilation, integration tests, and a fresh migration check.
