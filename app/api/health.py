"""Health check endpoints — liveness and readiness."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness probe — process is running."""
    return HealthResponse(status="alive")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness probe — dependencies are ready."""
    return HealthResponse(status="ready")
