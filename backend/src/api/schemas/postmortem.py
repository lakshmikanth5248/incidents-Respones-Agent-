"""
Post-Mortem Schemas.
Feature 11: Post-Mortem Generation (API-009, API-010, FR-053–FR-057).
Feature 12: Post-Mortem Confirmation and Memory Candidate (FR-056, FR-058–FR-066, DM-005).

Defines request and response schemas for post-mortem generation, retrieval, and confirmation.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


RootCauseSource = Literal[
    "current_incident",
    "human",
    "historical_memory",
    "inference",
    "unknown",
]

ResolutionEffectiveness = Literal[
    "effective",
    "ineffective",
    "inconclusive",
    "unknown",
]

PostMortemStatus = Literal["draft", "confirmed"]

# Allowed memory candidate entry types (FR-058, DM-005)
MemoryCandidateEntryType = Literal[
    "root_cause",
    "resolution",
    "lesson",
    "failed_approach",
    "runbook_outcome",
    "prevention",
]


class TimelineEvent(BaseModel):
    """Chronological event in the incident response lifecycle."""
    timestamp: Optional[str] = None
    phase: str  # detection | investigation | remediation | verification
    description: str


class CorrectionItem(BaseModel):
    """
    A single engineer-supplied field-level correction applied to the post-mortem draft.

    The agent records both the original and corrected values, ensuring provenance is
    preserved and corrections are never silently overwritten (FR-056, D-12).
    """
    model_config = ConfigDict(extra="ignore")

    field: str = Field(..., description="Post-mortem field being corrected (e.g. 'root_cause')")
    original: Optional[str] = Field(default=None, description="Original value from the draft")
    corrected: str = Field(..., description="Engineer-supplied corrected value")
    rationale: Optional[str] = Field(default=None, description="Optional explanation for the correction")


class MemoryCandidateEntry(BaseModel):
    """
    A single memory candidate entry proposed for Hindsight retention (FR-058, DM-005).

    These are composed from the confirmed post-mortem, not from the draft.
    Only entries supported by the confirmed post-mortem are included.
    """
    model_config = ConfigDict(extra="ignore")

    entry_type: MemoryCandidateEntryType
    service: str
    component: Optional[str] = None
    body: str = Field(..., description="The experience content to be retained")
    confidence: str = Field(default="confirmed", description="high | medium | low | confirmed")
    outcome_label: Optional[str] = None
    source_incident_ref: str = Field(..., description="The source incident ID")
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Evidence tracing this entry to a confirmed post-mortem field",
    )


class PostMortemGenerateRequest(BaseModel):
    """Payload for generating a draft post-mortem."""
    include_memory_reference: bool = Field(
        default=True,
        description="Whether to cite recalled historical memories in the post-mortem draft (UC-08 A-2)",
    )
    simulate_failure: Optional[str] = Field(
        default=None,
        description="Optional failure simulation ('unavailable') for testing model outage handling",
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional additional operator instructions for the generation prompt",
    )


class PostMortemConfirmRequest(BaseModel):
    """
    Payload for confirming a post-mortem draft (FR-056, D-12).

    Confirmation is the human gate that makes the incident's experience eligible for
    retention in Hindsight (FR-058, RP-006). The server validates all fields; the
    ``confirmed: true`` frontend flag alone is NOT trusted.

    Corrections are optional field-level overrides the engineer may supply at
    review time. Each correction is validated and applied before candidate generation.
    """

    model_config = ConfigDict(extra="ignore")

    reviewer: Optional[str] = Field(
        default=None,
        description="Explicit reviewer identity. Defaults to the X-Operator header.",
    )
    review_notes: Optional[str] = Field(
        default=None,
        description="Optional review notes recorded against the confirmation.",
    )
    corrections: List[CorrectionItem] = Field(
        default_factory=list,
        description=(
            "Optional list of engineer-supplied field corrections applied to the "
            "post-mortem draft before memory candidate composition. "
            "Valid correctable fields: root_cause, root_cause_source, root_cause_confidence, "
            "resolution, summary, impact."
        ),
    )


class PostMortemResponse(BaseModel):
    """
    Structured post-mortem document.

    Conforms to PRD FR-054 required sections:
      summary, impact, timeline, symptom_description, root_cause, resolution,
      resolution_effectiveness, contributing_factors, what_went_well, what_did_not,
      lessons, preventive_actions, unknowns, status = draft.

    Feature 12 additions:
      corrections, memory_candidates (populated only after confirmation).
    """
    id: str
    incident_id: str
    status: PostMortemStatus = "draft"
    summary: str
    impact: str
    timeline: List[TimelineEvent] = Field(default_factory=list)
    symptom_description: str
    root_cause: str
    root_cause_source: RootCauseSource
    root_cause_confidence: str
    resolution: str
    resolution_effectiveness: str
    contributing_factors: List[str] = Field(default_factory=list)
    what_went_well: List[str] = Field(default_factory=list)
    what_did_not: List[str] = Field(default_factory=list)
    lessons: List[str] = Field(default_factory=list)
    preventive_actions: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    memory_references: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    corrections: List[Dict[str, Any]] = Field(default_factory=list)
    memory_candidates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Memory candidate entries proposed for Hindsight retention. "
            "Populated only after the post-mortem is confirmed (FR-058, DM-005)."
        ),
    )
    confirmed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
