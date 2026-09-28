"""
Post-Mortem Database Model.
Feature 11: Post-Mortem Generation (API-009, API-010, FR-053–FR-057, DM-004).
Feature 12: Post-Mortem Confirmation and Memory Candidate (FR-056, FR-058–FR-066, DM-005).

Persists the structured post-mortem document derived from recorded incident data,
analysis findings, human resolution decisions, and outcome verification evidence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PostMortem(Base):
    """
    Structured Post-Mortem Document.

    Status transitions: draft -> confirmed.
    Acts as the source document for Hindsight experience retention (FR-058, DM-004).
    """

    __tablename__ = "postmortems"

    id = Column(String(64), primary_key=True, index=True)
    incident_id = Column(
        String(32),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String(32), nullable=False, default="draft")  # draft | confirmed

    # Core narrative sections (FR-054)
    summary = Column(Text, nullable=False)
    impact = Column(Text, nullable=False)
    timeline = Column(JSON, nullable=False, default=list)  # list[dict]
    symptom_description = Column(Text, nullable=False)

    # Root Cause with Provenance & Confidence (FR-055, FR-057)
    root_cause = Column(Text, nullable=False)
    root_cause_source = Column(
        String(32),
        nullable=False,
        default="unknown"
    )  # current_incident | human | historical_memory | inference | unknown
    root_cause_confidence = Column(String(16), nullable=False, default="medium")  # high | medium | low

    # Resolution & Verified Effectiveness (FR-054)
    resolution = Column(Text, nullable=False)
    resolution_effectiveness = Column(
        String(32),
        nullable=False,
        default="unknown"
    )  # effective | ineffective | inconclusive | unknown

    # Learnings & Follow-up Items (FR-054)
    contributing_factors = Column(JSON, nullable=False, default=list)  # list[str]
    what_went_well = Column(JSON, nullable=False, default=list)        # list[str]
    what_did_not = Column(JSON, nullable=False, default=list)          # list[str]
    lessons = Column(JSON, nullable=False, default=list)               # list[str]
    preventive_actions = Column(JSON, nullable=False, default=list)    # list[str]
    unknowns = Column(JSON, nullable=False, default=list)              # list[str]

    # Memory & Provenance references
    memory_references = Column(JSON, nullable=False, default=list)     # list[dict]
    provenance = Column(JSON, nullable=False, default=list)            # list[dict]

    # Confirmation gate (FR-056, D-12)
    reviewed_by = Column(String(64), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Engineer-supplied corrections applied at confirmation time (FR-056)
    # list[{"field": str, "original": str, "corrected": str, "rationale": str}]
    corrections = Column(JSON, nullable=False, default=list)

    # Memory candidates composed from the confirmed post-mortem (FR-058, DM-005)
    # list[{"entry_type": str, "service": str, "body": str, "confidence": str, "provenance": dict, ...}]
    memory_candidates = Column(JSON, nullable=False, default=list)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "status": self.status,
            "summary": self.summary,
            "impact": self.impact,
            "timeline": self.timeline or [],
            "symptom_description": self.symptom_description,
            "root_cause": self.root_cause,
            "root_cause_source": self.root_cause_source,
            "root_cause_confidence": self.root_cause_confidence,
            "resolution": self.resolution,
            "resolution_effectiveness": self.resolution_effectiveness,
            "contributing_factors": self.contributing_factors or [],
            "what_went_well": self.what_went_well or [],
            "what_did_not": self.what_did_not or [],
            "lessons": self.lessons or [],
            "preventive_actions": self.preventive_actions or [],
            "unknowns": self.unknowns or [],
            "memory_references": self.memory_references or [],
            "provenance": self.provenance or [],
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "corrections": self.corrections or [],
            "memory_candidates": self.memory_candidates or [],
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
