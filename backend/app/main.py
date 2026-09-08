"""
ModelWatch FastAPI application entrypoint.

M1 scope: application bootstrap + health check only.
Routers for models/versions/features/etc. are added in later milestones.
"""
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.reference import router as reference_router
from app.api.registry import router as registry_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="ML data-drift monitoring platform.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(registry_router)
app.include_router(reference_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Basic liveness check. Does not touch the database or Redis in M1."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
