"""
Resolution Record Database Model.
Conforms to PRD §12.8 (FR-049–FR-052), UC-07, W-11, W-12.

Persists the engineer's authoritative resolution decision after a production incident.
The AI cannot resolve incidents — the engineer decides.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResolutionRecord(Base):
    """
    Persists the authoritative human resolution decision for an incident.

    Idempotency: one resolution record per incident_id.
    An incident cannot be closed without either a resolution record OR
    an explicit close_without_resolution=True flag.

    Conforms to:
      - FR-049: record the resolution actually applied
      - FR-050: record which recommended actions were followed/skipped/attempted-failed
      - FR-051: support unknown / low-confidence outcome; propagate confidence marker
      - FR-052: no closed state without recorded resolution or explicit decision to close without one
    """

    __tablename__ = "resolution_records"

    # Primary link
    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(
        String(32),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,          # Idempotency: one record per incident
        index=True,
    )

    # Resolution content (FR-049)
    actions_taken = Column(JSON, nullable=False, default=list)   # list[str]
    runbook_id = Column(String(64), nullable=True)
    runbook_version = Column(String(32), nullable=True)
    root_cause = Column(Text, nullable=True)          # "unknown" is a valid value (FR-051)
    contributing_factors = Column(JSON, nullable=False, default=list)  # list[str]
    result = Column(Text, nullable=True)              # Observed post-action result
    outcome = Column(String(32), nullable=False)      # successful | ineffective | inconclusive | unknown

    # Recommendation tracking (FR-050)
    recommendation_outcomes = Column(JSON, nullable=False, default=list)  # list[RecommendationOutcome]

    # Close-without-resolution (FR-052)
    close_without_resolution = Column(Boolean, nullable=False, default=False)
    close_without_resolution_reason = Column(Text, nullable=True)

    # Human authorship
    operator = Column(String(64), nullable=False, default="sre-operator")
    operator_notes = Column(Text, nullable=True)

    # Confidence marker for low-confidence outcomes (FR-051)
    outcome_confidence = Column(String(16), nullable=False, default="high")  # high | low

    # Timestamps
    resolved_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        """Serialise to JSON-safe dict."""
        return {
            "resolution_id": self.id,
            "incident_id": self.incident_id,
            "actions_taken": self.actions_taken or [],
            "runbook_id": self.runbook_id,
            "runbook_version": self.runbook_version,
            "root_cause": self.root_cause,
            "contributing_factors": self.contributing_factors or [],
            "result": self.result,
            "outcome": self.outcome,
            "outcome_confidence": self.outcome_confidence,
            "recommendation_outcomes": self.recommendation_outcomes or [],
            "close_without_resolution": self.close_without_resolution,
            "close_without_resolution_reason": self.close_without_resolution_reason,
            "operator": self.operator,
            "operator_notes": self.operator_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
