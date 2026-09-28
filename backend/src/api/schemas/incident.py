"""
Incident API Schemas and DTOs.
Conforms to PRD §12.2 (API-001, API-002, API-003, API-004), BE-015 error model, and Feature 2 Lifecycle.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class IncidentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symptom_description: str = Field(
        ...,
        description="Free-form text describing observed symptoms (required)"
    )
    service: Optional[str] = Field(
        default=None,
        description="Optional affected service name (e.g., payment-api)"
    )
    environment: Optional[str] = Field(
        default=None,
        description="Optional environment (production, staging, development, unknown)"
    )
    severity: Optional[str] = Field(
        default=None,
        description="Optional severity level (critical, high, medium, low, unknown)"
    )
    observed_at: Optional[str] = Field(
        default=None,
        description="Optional timestamp when the problem was observed"
    )
    error_text: Optional[List[str]] = Field(
        default=None,
        description="Optional list of error messages or exception strings"
    )
    log_excerpt: Optional[str] = Field(
        default=None,
        description="Optional log excerpt"
    )
    recent_changes: Optional[List[str]] = Field(
        default=None,
        description="Optional descriptions of recent deploys, config changes, or migrations"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional free-form additional context dictionary"
    )
    is_synthetic: Optional[bool] = Field(
        default=False,
        description="Whether this incident is part of synthetic demo corpus (DM-015)"
    )


class IncidentPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Optional[str] = None
    environment: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    expected_revision: Optional[int] = Field(
        default=None,
        description="Optimistic locking: expected revision of the incident before applying changes."
    )
    from_status: Optional[str] = Field(
        default=None,
        description="Expected current state to guard against conflicting concurrent transitions."
    )
    error_text: Optional[List[str]] = None
    log_excerpt: Optional[str] = None
    recent_changes: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    symptom_description_correction: Optional[str] = None


class StateTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: str = Field(
        ...,
        description="Target lifecycle state (analyzing, analyzed, recommendation_ready, resolving, resolved, closed, etc.)"
    )
    expected_revision: Optional[int] = Field(
        default=None,
        description="Optimistic locking revision guard."
    )
    from_status: Optional[str] = Field(
        default=None,
        description="Expected previous status to detect concurrent modifications."
    )
    actor: Optional[str] = Field(
        default="sre-operator",
        description="Identity of the operator performing the transition."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional human-readable operational justification."
    )


class IncidentResponse(BaseModel):
    id: str
    status: str
    state: str = "created"
    raw_symptom_description: str
    symptoms_raw: str
    symptoms_normalized: Optional[str] = None
    service: str
    environment: str
    severity: str
    normalized: Dict[str, Any]
    error_signatures: List[str] = []
    failure_mode_label: str = "unknown"
    affected_components: List[str] = []
    recent_changes: List[Any] = []
    context: Dict[str, Any] = {}
    created_at: str
    detected_at: Optional[str] = None
    resolved_at: Optional[str] = None
    updated_at: Optional[str] = None
    operator: str = "sre-operator"
    is_synthetic: bool = False
    possible_duplicate: bool = False
    duplicate_of: Optional[str] = None
    revision: int = 1
    analysis_revision: int = 0
    memory_status: Optional[str] = None
    resolution_status: str = "unresolved"
    postmortem_status: str = "none"
    verification_status: str = "unverified"
    analysis_id: Optional[str] = None


class IncidentListResponse(BaseModel):
    incidents: List[IncidentResponse]
    total: int
    limit: int
    offset: int


class AuditEventResponse(BaseModel):
    id: int
    incident_id: Optional[str]
    action: str
    actor: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    outcome: str
    details: Dict[str, Any] = {}
    timestamp: Optional[str] = None


class AuditListResponse(BaseModel):
    incident_id: str
    events: List[AuditEventResponse]
    total: int


class IncidentMemoryResponse(BaseModel):
    incident_id: str
    memory_status: str
    recall_record: Dict[str, Any]
    entries: List[Dict[str, Any]] = Field(default_factory=list)
