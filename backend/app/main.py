from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.db.session import SessionLocal

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API foundation for Café Aramesh Smart Menu.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness probe; does not depend on external services."""
    return {"status": "ok", "service": "cafe-aramesh-api"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    """Readiness probe; verifies that PostgreSQL accepts a simple query."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ready", "database": "ok"}


app.include_router(v1_router)
