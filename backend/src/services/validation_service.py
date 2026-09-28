"""
Validation and Secret Scanning Service.
Conforms to PRD BE-010, BE-012, SEC-002, SEC-007, SEC-008, SEC-015, ERR-05, and Feature 2 State Machine.
Provides strict input validation, secret scanning, and lifecycle transition enforcement.
"""

import re
from typing import List, Optional, Set, Dict
from pydantic import BaseModel
from src.config import settings


class SecretScanResult(BaseModel):
    has_secrets: bool
    detected_types: List[str] = []


# Compiled patterns for secret detection
SECRET_PATTERNS = [
    ("api_key", re.compile(r"\b(?:sk-[a-zA-Z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{50,}|xox[baprs]-[0-9a-zA-Z\-]{10,})\b", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----", re.IGNORECASE)),
    ("authorization_header", re.compile(r"\b(?:Bearer\s+[a-zA-Z0-9_\-\.]{20,}|Basic\s+[a-zA-Z0-9+/=]{20,})\b", re.IGNORECASE)),
    ("password", re.compile(r'(?:\b(?:password|passwd|pwd|secret_key|client_secret)\s*[:=]\s*["\']?[^\s"\'\,\;]{4,}["\']?|://[^:/\s]+:[^@/\s]+@)', re.IGNORECASE)),
]

VALID_SEVERITIES = {"critical", "high", "medium", "low", "unknown"}
VALID_ENVIRONMENTS = {"production", "staging", "development", "test", "unknown"}
VALID_STATUSES = {
    "created",
    "analyzing",
    "investigating",
    "analyzed",
    "recommendation_ready",
    "resolving",
    "mitigated",
    "resolved",
    "closed"
}

# Controlled Lifecycle State Machine Graph (Feature 2 & PRD FR-009, D-13)
LIFECYCLE_TRANSITIONS: Dict[str, Set[str]] = {
    "created": {"analyzing", "investigating", "closed"},
    "analyzing": {"analyzed", "investigating", "closed"},
    "investigating": {"analyzing", "analyzed", "recommendation_ready", "resolving", "mitigated", "closed"},
    "analyzed": {"recommendation_ready", "resolving", "mitigated", "analyzing", "closed"},
    "recommendation_ready": {"resolving", "mitigated", "analyzing", "closed"},
    "resolving": {"resolved", "mitigated", "investigating", "closed"},
    "mitigated": {"resolved", "resolving", "investigating", "closed"},
    "resolved": {"closed"},  # Forbidden: resolved -> created, resolved -> analyzing
    "closed": set(),  # Terminal state: No transitions allowed
}


class ValidationService:
    """Validates incident requests, lifecycle transitions, and checks for sensitive secrets."""

    @classmethod
    def scan_for_secrets(cls, text: Optional[str]) -> SecretScanResult:
        """Scan text for obvious credential-shaped or secret-like values."""
        if not text or not isinstance(text, str):
            return SecretScanResult(has_secrets=False, detected_types=[])

        detected_types: Set[str] = set()
        for type_name, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                detected_types.add(type_name)

        return SecretScanResult(
            has_secrets=bool(detected_types),
            detected_types=sorted(list(detected_types))
        )

    @classmethod
    def validate_symptom_description(cls, text: Optional[str]) -> str:
        """Strictly validates the symptom description."""
        if text is None or not isinstance(text, str):
            raise ValueError("MINIMUM_INPUT_REQUIRED: A symptom description is required to create an incident.")

        cleaned = text.strip()
        if not cleaned:
            raise ValueError("MINIMUM_INPUT_REQUIRED: A symptom description is required to create an incident.")

        if len(cleaned) > settings.MAX_SYMPTOM_LENGTH:
            raise ValueError(f"PAYLOAD_LIMIT_EXCEEDED: Symptom description exceeds max length of {settings.MAX_SYMPTOM_LENGTH} characters.")

        return cleaned

    @classmethod
    def validate_severity(cls, severity: Optional[str]) -> str:
        """Validate severity against permitted enum values."""
        if severity is None:
            return "unknown"
        val = severity.lower().strip()
        if val not in VALID_SEVERITIES:
            raise ValueError(f"INVALID_ENUM_VALUE: Severity must be one of {sorted(list(VALID_SEVERITIES))}, got '{severity}'.")
        return val

    @classmethod
    def validate_environment(cls, environment: Optional[str]) -> str:
        """Validate environment against permitted enum values."""
        if environment is None:
            return "unknown"
        val = environment.lower().strip()
        if val not in VALID_ENVIRONMENTS:
            raise ValueError(f"INVALID_ENUM_VALUE: Environment must be one of {sorted(list(VALID_ENVIRONMENTS))}, got '{environment}'.")
        return val

    @classmethod
    def validate_status_transition(cls, current_status: str, new_status: str) -> None:
        """
        Enforces controlled lifecycle state machine transitions.
        Conforms strictly to Feature 2 state-machine rules and terminal-state protection.
        """
        cur = current_status.lower().strip()
        nxt = new_status.lower().strip()

        if nxt not in VALID_STATUSES:
            raise ValueError(
                f"INVALID_STATUS: Unknown incident status '{new_status}'. Allowed statuses: {sorted(list(VALID_STATUSES))}."
            )

        if cur == "closed":
            raise ValueError("TERMINAL_STATE: Closed incidents cannot transition to any other state. Terminal states remain terminal.")

        if cur == nxt:
            return  # No-op transition

        allowed = LIFECYCLE_TRANSITIONS.get(cur, set())
        if nxt not in allowed:
            raise ValueError(
                f"INVALID_STATE_TRANSITION: Cannot transition incident from '{cur}' to '{nxt}'. "
                f"Allowed transitions from '{cur}': {sorted(list(allowed))}."
            )
