from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": "qa-intelligence-hub-api",
        "version": settings.app_version,
        "environment": settings.environment,
    }