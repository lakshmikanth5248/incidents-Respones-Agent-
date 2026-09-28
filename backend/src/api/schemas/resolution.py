"""
Resolution API Schemas and DTOs.
Conforms to PRD §12.8 (FR-049–FR-052, FR-044), UC-07, W-12.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Allowed enum values
# ---------------------------------------------------------------------------

ALLOWED_OUTCOMES = {"successful", "ineffective", "inconclusive", "unknown"}
ALLOWED_RECOMMENDATION_STATUSES = {"followed", "skipped", "attempted_failed"}


# ---------------------------------------------------------------------------
# Sub-objects
# ---------------------------------------------------------------------------

class RecommendationOutcome(BaseModel):
    """
    Records what happened to a specific advisory recommendation (FR-044, FR-050).

    status values:
      followed          — engineer followed the recommendation; it worked
      skipped           — engineer did not attempt this recommendation
      attempted_failed  — engineer attempted but the recommendation did not work
    """
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(
        ...,
        description="ID of the RecommendationItem this outcome records."
    )
    status: str = Field(
        ...,
        description="One of: followed | skipped | attempted_failed"
    )
    note: Optional[str] = Field(
        default=None,
        description="Optional operator note about this recommendation outcome."
    )

    @model_validator(mode="after")
    def validate_status(self) -> "RecommendationOutcome":
        if self.status not in ALLOWED_RECOMMENDATION_STATUSES:
            raise ValueError(
                f"recommendation_outcome.status must be one of "
                f"{sorted(ALLOWED_RECOMMENDATION_STATUSES)}, got '{self.status}'"
            )
        return self


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ResolveIncidentRequest(BaseModel):
    """
    Request body for POST /api/incidents/{id}/resolve.

    Closing rule (FR-052):
      - close_without_resolution=False (default): actions_taken and outcome are REQUIRED.
      - close_without_resolution=True: close_without_resolution_reason is REQUIRED;
        actions_taken and outcome MAY be omitted.
    """
    model_config = ConfigDict(extra="forbid")

    # --- Applied resolution ---
    actions: List[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of actions the engineer actually applied. "
            "Required unless close_without_resolution=True."
        )
    )
    runbook_id: Optional[str] = Field(
        default=None,
        description="ID of the runbook followed (if any)."
    )
    runbook_version: Optional[str] = Field(
        default=None,
        description="Version of the runbook followed."
    )
    contributing_factors: List[str] = Field(
        default_factory=list,
        description="Contributing environmental or systemic factors identified."
    )
    root_cause: Optional[str] = Field(
        default=None,
        description=(
            "Engineer-stated root cause. 'unknown' is a valid value (FR-051). "
            "Where stated, this takes precedence over the agent hypothesis (FR-057)."
        )
    )
    result: Optional[str] = Field(
        default=None,
        description="Observed outcome after applying the resolution steps."
    )
    outcome: Optional[str] = Field(
        default=None,
        description=(
            "Resolution outcome: successful | ineffective | inconclusive | unknown. "
            "Required unless close_without_resolution=True."
        )
    )

    # --- Recommendation tracking (FR-050) ---
    recommendation_outcomes: List[RecommendationOutcome] = Field(
        default_factory=list,
        description=(
            "Records what happened to each advisory recommendation: "
            "followed, skipped, or attempted_failed."
        )
    )

    # --- Operator metadata ---
    operator_notes: Optional[str] = Field(
        default=None,
        description="Free-form engineer notes about the resolution."
    )

    # --- Close-without-resolution gate (FR-052) ---
    close_without_resolution: bool = Field(
        default=False,
        description=(
            "Explicit flag to close the incident without recording a resolution. "
            "Requires close_without_resolution_reason."
        )
    )
    close_without_resolution_reason: Optional[str] = Field(
        default=None,
        description=(
            "Mandatory reason when close_without_resolution=True. "
            "Documents the explicit decision not to record a resolution."
        )
    )

    @model_validator(mode="after")
    def validate_close_rules(self) -> "ResolveIncidentRequest":
        if self.close_without_resolution:
            # Reason is required for the explicit close decision
            if not self.close_without_resolution_reason or not self.close_without_resolution_reason.strip():
                raise ValueError(
                    "close_without_resolution_reason is required when close_without_resolution=True."
                )
        else:
            # Normal close: actions and outcome are required
            if not self.actions:
                raise ValueError(
                    "actions must contain at least one entry when close_without_resolution=False."
                )
            if not self.outcome:
                raise ValueError(
                    "outcome is required when close_without_resolution=False."
                )
            if self.outcome not in ALLOWED_OUTCOMES:
                raise ValueError(
                    f"outcome must be one of {sorted(ALLOWED_OUTCOMES)}, got '{self.outcome}'."
                )
        return self


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class ResolutionResponse(BaseModel):
    """Full resolution record returned after POST /api/incidents/{id}/resolve."""

    resolution_id: str
    incident_id: str

    actions_taken: List[str] = []
    runbook_id: Optional[str] = None
    runbook_version: Optional[str] = None
    root_cause: Optional[str] = None
    contributing_factors: List[str] = []
    result: Optional[str] = None
    outcome: str
    outcome_confidence: str = "high"

    recommendation_outcomes: List[Dict[str, Any]] = []

    close_without_resolution: bool = False
    close_without_resolution_reason: Optional[str] = None

    operator: str = "sre-operator"
    operator_notes: Optional[str] = None

    resolved_at: str
    created_at: str

    # Incident state after resolution
    incident_status: str
    resolution_status: str
