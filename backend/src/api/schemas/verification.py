"""
Verification Schemas.
Feature 10: Resolution Outcome Verification.

Defines the request and response models for resolution outcome verification.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


VerificationStatus = Literal["confirmed", "inconclusive", "failed", "unknown"]
MetricDirection = Literal["improved", "degraded", "unchanged", "unknown"]
EvidenceAssessment = Literal[
    "supports_recovery",
    "indicates_failure",
    "conflicting",
    "inconclusive",
    "unverified",
]


class VerificationRequest(BaseModel):
    """
    Input payload for resolution outcome verification.

    Supports:
      - before metrics
      - after metrics
      - observations
      - operator result
      - verification notes
    """
    before_metrics: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Baseline telemetry or state metrics prior to resolution action",
    )
    after_metrics: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Telemetry or state measurements observed after resolution action",
    )
    observations: Optional[List[str]] = Field(
        default_factory=list,
        description="Qualitative engineering observations following action",
    )
    operator_result: Optional[str] = Field(
        None,
        description="Declared operator outcome (successful, ineffective, inconclusive, unknown)",
    )
    verification_notes: Optional[str] = Field(
        None,
        description="Verifying engineer's reasoning, notes, or operational context",
    )


class ObservedChange(BaseModel):
    """Structured change for a single metric between before and after states."""
    metric: str
    before: Any
    after: Any
    delta: Optional[str] = None
    direction: MetricDirection = "unknown"
    details: str


class VerificationEvidenceItem(BaseModel):
    """Individual item of verification evidence evaluating the outcome."""
    source: str
    claim: str
    assessment: EvidenceAssessment
    details: str


class VerificationResponse(BaseModel):
    """
    Structured outcome verification response.

    Contains:
      - verification_status (confirmed | inconclusive | failed | unknown)
      - before_state (no fabricated measurements)
      - after_state (no fabricated measurements)
      - observed_changes
      - evidence
    """
    id: str
    incident_id: str
    resolution_id: Optional[str] = None
    verification_status: VerificationStatus
    operator_result: Optional[str] = None
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    observed_changes: List[ObservedChange] = Field(default_factory=list)
    evidence: List[VerificationEvidenceItem] = Field(default_factory=list)
    verification_notes: Optional[str] = None
    verified_by: str = "sre-verifier"
    verified_at: str
    created_at: str
    incident_status: Optional[str] = None
