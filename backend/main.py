from fastapi import FastAPI

from app.core.config import settings
from app.routers import health

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for the QA Intelligence Hub platform.",
)

app.include_router(health.router)