"""
Health Check API.
Conforms to PRD §19.2 (DEP-012, API-016).
Reports application status, database connectivity, and environment metadata.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.config import settings
from src.data.database import get_db
from src.memory.service import memory_service

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK, summary="Service Health Check (API-016)")
def health_check(db: Session = Depends(get_db)):
    """Check connectivity to core dependencies."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    mem_healthy, mem_status = memory_service.health_check()

    is_healthy = (db_status == "connected") and mem_healthy
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if is_healthy else "degraded",
            "environment": settings.APP_ENV,
            "version": "0.1.0",
            "dependencies": {
                "database": db_status,
                "memory": mem_status,
                "model_provider": settings.MODEL_PROVIDER,
            }
        }
    )
