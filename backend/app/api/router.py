"""Versioned API router."""

from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.system import router as system_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(system_router)


@router.get("/health", tags=["system"])
def versioned_health() -> dict[str, str]:
    return {"status": "healthy"}
