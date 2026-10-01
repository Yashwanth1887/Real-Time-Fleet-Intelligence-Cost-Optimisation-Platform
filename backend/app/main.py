"""FastAPI application entry point."""

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.router import router as api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("fleetguard.http")

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])
app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_id if len(supplied_id) <= 64 and supplied_id.replace("-", "").replace("_", "").isalnum() else str(uuid4())
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; frame-ancestors 'none'"
    )
    logger.info("request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
                request_id, request.method, request.url.path, response.status_code,
                (perf_counter() - started) * 1000)
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Database service is unavailable"})


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"application": "FleetGuard", "status": "running", "version": settings.app_version}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
