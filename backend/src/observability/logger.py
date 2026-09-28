"""
Observability and Structured Logging Module.
Conforms to PRD BE-011, BE-017, SEC-002, SEC-006, T-SEC-02.
Enforces secret redaction at the logging layer and includes request correlation IDs.
"""

import logging
import re
import sys
from contextvars import ContextVar
from typing import Optional

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Secret detection / redaction patterns for logging layer
SECRET_LOG_PATTERNS = [
    # Common API keys (OpenAI, Anthropic, AWS, GitHub, Slack)
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE), "[REDACTED_AWS_KEY]"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"xox[baprs]-[0-9a-zA-Z\-]{10,}", re.IGNORECASE), "[REDACTED_SLACK_TOKEN]"),
    # Bearer tokens & JWTs
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+"), "[REDACTED_JWT]"),
    # Private keys
    (re.compile(r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z0-9_-]*PRIVATE KEY-----", re.IGNORECASE), "[REDACTED_PRIVATE_KEY]"),
    # Passwords in URLs / connection strings
    (re.compile(r"://([^:]+):([^@\s]+)@"), r"://\1:[REDACTED_PASSWORD]@"),
    # Password key-value pairs
    (re.compile(r'(password|passwd|secret|token|api_key|auth_token)\s*[:=]\s*["\']?[^"\'\s,;]{4,}["\']?', re.IGNORECASE), r"\1=[REDACTED]"),
]


def redact_secrets_text(text: str) -> str:
    """Scrub sensitive credential-shaped patterns from text."""
    if not isinstance(text, str):
        return text
    scrubbed = text
    for pattern, replacement in SECRET_LOG_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


class RedactingFormatter(logging.Formatter):
    """Logging formatter that redacts secrets and appends correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        # Inject correlation_id if available
        cid = correlation_id_ctx.get() or getattr(record, "correlation_id", "-")
        record.correlation_id = cid

        original_message = super().format(record)
        return redact_secrets_text(original_message)


def setup_logger(name: str = "incident_agent", level: str = "INFO") -> logging.Logger:
    """Configures and returns a structured logger with redaction."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [req:%(correlation_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


# Global logger instance
logger = setup_logger()
