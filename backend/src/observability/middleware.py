"""
Observability and Security Middleware.
Conforms to PRD BE-017, SEC-007, and API response requirements.
Handles correlation IDs, execution timing, and request size guardrails.
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from src.config import settings
from src.observability.logger import logger, correlation_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a correlation ID, propagated across context and headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        corr_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or str(uuid.uuid4())
        )
        token = correlation_id_ctx.set(corr_id)
        request.state.correlation_id = corr_id

        start_time = time.time()
        logger.info(f"request.started path={request.url.path} method={request.method}")

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = corr_id
            logger.info(
                f"request.completed path={request.url.path} method={request.method} "
                f"status={response.status_code} duration_ms={duration_ms}"
            )
            return response
        finally:
            correlation_id_ctx.reset(token)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces request payload size limits to prevent unbounded context growth (SEC-007)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > settings.MAX_PAYLOAD_BYTES:
                    logger.warning(f"request.payload_too_large size={length} limit={settings.MAX_PAYLOAD_BYTES}")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Payload size {length} bytes exceeds maximum allowed {settings.MAX_PAYLOAD_BYTES} bytes.",
                                "retryable": False,
                                "details": {"max_bytes": settings.MAX_PAYLOAD_BYTES, "received_bytes": length}
                            }
                        }
                    )
            except ValueError:
                pass
        return await call_next(request)
