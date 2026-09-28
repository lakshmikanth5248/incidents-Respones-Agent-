"""
Incident Response Agent - FastAPI Backend Application.
Conforms to PRD BE-001, BE-002, BE-011, BE-015, BE-017, BE-018.
Single deployable backend service implementing Feature 1: Incident Intake & Normalization.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.config import settings
from src.data.database import init_db
from src.observability.logger import logger
from src.observability.middleware import CorrelationIdMiddleware, RequestSizeLimitMiddleware
from src.api.errors import (
    APIException,
    api_exception_handler,
    validation_exception_handler,
    db_exception_handler,
    generic_exception_handler,
)
from src.api.routes import incidents, health, memory, runbooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(f"backend.startup env={settings.APP_ENV} db={settings.DATABASE_URL.split('@')[-1]}")
    # Initialize relational database tables (DEP-003)
    init_db()
    logger.info("backend.database_initialized tables_ready=true")
    yield
    logger.info("backend.shutdown complete")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    application = FastAPI(
        title="Incident Response Agent API",
        description=(
            "Hindsight-Enabled Incident Memory and Resolution Assistant for Site Reliability Engineers. "
            "Feature 1: Incident Intake & Normalization."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Security & Observability Middleware (evaluated in reverse order)
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(RequestSizeLimitMiddleware)

    # CORS configuration (SEC-003, DEP-001)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.CORS_ORIGIN,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Global Exception Handlers conforming to BE-015
    application.add_exception_handler(APIException, api_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(SQLAlchemyError, db_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # 3. Mount API Routers under /api
    application.include_router(incidents.router, prefix=settings.API_PREFIX)
    application.include_router(memory.router, prefix=settings.API_PREFIX)
    application.include_router(runbooks.router, prefix=settings.API_PREFIX)
    application.include_router(health.router, prefix=settings.API_PREFIX)
    from src.api.routes import frontend_compat
    application.include_router(frontend_compat.router, prefix=settings.API_PREFIX)

    # 4. Mount Frontend Production Single-Page App if built
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        application.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static_frontend")

    return application




app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
