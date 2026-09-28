"""
Error Handling and Standard Error Model.
Conforms strictly to PRD BE-015, ERR-05, ERR-06, and Part 2 §15.
Guarantees consistent error envelopes and prevents secret leakage.
"""

from typing import Dict, Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.observability.logger import logger


class APIException(Exception):
    """Domain-specific API Exception conforming to BE-015."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)


def build_error_response(
    code: str,
    message: str,
    status_code: int,
    retryable: bool = False,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Build standard JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "details": details or {}
            }
        }
    )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    logger.warning(
        f"api.error code={exc.code} status={exc.status_code} "
        f"msg={exc.message} path={request.url.path}"
    )
    return build_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        retryable=exc.retryable,
        details=exc.details
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(f"request.validation_failed errors={exc.errors()} path={request.url.path}")

    # Sanitize Pydantic v2 errors: ctx["error"] may be an Exception object,
    # which is not JSON-serializable. Convert to string.
    def _sanitize_error(err: dict) -> dict:
        sanitized = {}
        for k, v in err.items():
            if k == "ctx" and isinstance(v, dict):
                sanitized[k] = {
                    ck: str(cv) if isinstance(cv, Exception) else cv
                    for ck, cv in v.items()
                }
            elif isinstance(v, Exception):
                sanitized[k] = str(v)
            else:
                sanitized[k] = v
        return sanitized

    sanitized_errors = [_sanitize_error(e) for e in exc.errors()]

    # Inspect if symptom_description is missing or empty
    for err in sanitized_errors:
        loc = err.get("loc", ())
        if "symptom_description" in loc:
            return build_error_response(
                code="MINIMUM_INPUT_REQUIRED",
                message="A symptom description is required to create an incident.",
                status_code=status.HTTP_400_BAD_REQUEST,
                retryable=False,
                details={"errors": sanitized_errors}
            )

    return build_error_response(
        code="INVALID_INPUT",
        message="Request validation failed. Ensure all fields adhere to the API contract.",
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        retryable=False,
        details={"errors": sanitized_errors}
    )


async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error(f"database.error error={str(exc)} path={request.url.path}")
    return build_error_response(
        code="DB_UNAVAILABLE",
        message="The incident database is unavailable. No changes were made.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable=True,
        details={}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"server.unexpected_error error={str(exc)} path={request.url.path}")
    return build_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        retryable=True,
        details={}
    )
