"""
Verification Record Database Model.
Feature 10: Resolution Outcome Verification.

Implements verification of what happened after the engineer's action.
Invariant: Do not assume an action worked merely because the engineer marked it successful.
Record available evidence. Do not manufacture measurements.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VerificationRecord(Base):
    """
    Persists resolution outcome verification results for an incident.

    Idempotency: one verification record per incident_id.
    Captures:
      - before_state: verbatim baseline metrics prior to action
      - after_state: verbatim measurements observed after action
      - observed_changes: structured delta and direction analysis
      - evidence: evidence items evaluating recovery claims
      - verification_status: confirmed | inconclusive | failed | unknown
    """

    __tablename__ = "verification_records"

    # Identifiers
    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(
        String(32),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    resolution_id = Column(String(64), nullable=True, index=True)

    # Outcome evaluation
    verification_status = Column(String(32), nullable=False)  # confirmed | inconclusive | failed | unknown
    operator_result = Column(String(32), nullable=True)        # operator's declared outcome

    # Structured states & evidence (no manufactured measurements)
    before_state = Column(JSON, nullable=False, default=dict)
    after_state = Column(JSON, nullable=False, default=dict)
    observed_changes = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)

    # Verification metadata
    verification_notes = Column(Text, nullable=True)
    verified_by = Column(String(64), nullable=False, default="sre-verifier")
    verified_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "verification_id": self.id,
            "incident_id": self.incident_id,
            "resolution_id": self.resolution_id,
            "verification_status": self.verification_status,
            "operator_result": self.operator_result,
            "before_state": self.before_state or {},
            "after_state": self.after_state or {},
            "observed_changes": self.observed_changes or [],
            "evidence": self.evidence or [],
            "verification_notes": self.verification_notes,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_postmortem_context(self) -> Dict[str, Any]:
        """Produce structured verification context for Post-Mortem generation (Feature 11)."""
        return {
            "verification_id": self.id,
            "verification_status": self.verification_status,
            "operator_result": self.operator_result,
            "before_state": self.before_state or {},
            "after_state": self.after_state or {},
            "observed_changes": self.observed_changes or [],
            "evidence": self.evidence or [],
            "verification_notes": self.verification_notes,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    def to_memory_candidate_context(self) -> Dict[str, Any]:
        """Produce structured verification context for Hindsight Memory Candidate retention (Feature 12)."""
        outcome_label = (
            "effective" if self.verification_status == "confirmed" else (
                "ineffective" if self.verification_status == "failed" else self.verification_status
            )
        )
        confidence = "high" if self.verification_status == "confirmed" else (
            "low" if self.verification_status in ("inconclusive", "unknown") else "high"
        )
        return {
            "verification_status": self.verification_status,
            "verified_outcome": outcome_label,
            "outcome_confidence": confidence,
            "verified_metrics_delta": [c.get("details") for c in (self.observed_changes or []) if "details" in c],
            "evidence_summary": [e.get("details") for e in (self.evidence or []) if "details" in e],
        }
