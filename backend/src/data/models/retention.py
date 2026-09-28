"""
Memory Retention Ledger Database Model.
Feature 13: Hindsight Retention (API-012, FR-058–FR-066, RP-009–RP-016, D-10, D-11, D-12).

One row per (incident_id, entry_key). The row is BOTH:
  - the idempotency ledger that prevents duplicate memory for the same entry (RP-015, D-10)
  - the preserved composed record that makes a failed write retryable (RP-014, FR-063, AC-24)

The entry_key is a deterministic function of the entry's identity (incident + type +
service + component + normalized body + outcome + confidence), so a repeated retain
request maps to the same row and therefore the same Hindsight memory_entry_id.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryRetention(Base):
    """
    Idempotency ledger and retry buffer for a single retained memory entry.

    status values:
      retained  — the entry exists in Hindsight; memory_entry_id is populated
      failed    — the write did not complete; the composed record is preserved for retry
    """

    __tablename__ = "memory_retentions"
    __table_args__ = (
        UniqueConstraint("incident_id", "entry_key", name="uq_memory_retention_incident_entry"),
        Index("ix_memory_retentions_incident_status", "incident_id", "status"),
    )

    id = Column(String(64), primary_key=True, index=True)

    # --- Idempotency identity (D-10, RP-015) ---
    incident_id = Column(
        String(32),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_key = Column(String(64), nullable=False, index=True)
    retain_id = Column(String(64), nullable=True, index=True)  # batch/operation identifier

    # --- Preserved composed record (RP-014, FR-063) ---
    entry_type = Column(String(64), nullable=False)
    service = Column(String(128), nullable=False)
    component = Column(String(128), nullable=True)
    body = Column(Text, nullable=False)
    outcome_label = Column(String(32), nullable=True)
    confidence = Column(String(16), nullable=True)
    source_incident_ref = Column(String(64), nullable=False)
    provenance_group_id = Column(String(64), nullable=True)
    is_synthetic = Column(Boolean, nullable=False, default=True)
    supersedes = Column(String(64), nullable=True)

    # --- Write outcome ---
    status = Column(String(32), nullable=False, default="failed", index=True)
    memory_entry_id = Column(String(64), nullable=True, index=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)

    # --- Human authorship (RP-011, D-12) ---
    confirmed_by = Column(String(64), nullable=True)
    postmortem_id = Column(String(64), nullable=True)

    # --- Timestamps ---
    retained_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    def to_payload(self) -> Dict[str, Any]:
        """Rebuild the exact Hindsight write payload from the preserved record."""
        return {
            "entry_type": self.entry_type,
            "service": self.service,
            "component": self.component,
            "body": self.body,
            "outcome_label": self.outcome_label,
            "confidence": self.confidence,
            "source_incident_ref": self.source_incident_ref,
            "provenance_group_id": self.provenance_group_id,
            "is_synthetic": self.is_synthetic,
            "supersedes": self.supersedes,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-safe dict."""
        return {
            "retention_id": self.id,
            "incident_id": self.incident_id,
            "retain_id": self.retain_id,
            "entry_key": self.entry_key,
            "entry_type": self.entry_type,
            "service": self.service,
            "component": self.component,
            "outcome_label": self.outcome_label,
            "confidence": self.confidence,
            "source_incident_ref": self.source_incident_ref,
            "status": self.status,
            "memory_entry_id": self.memory_entry_id,
            "error": self.error,
            "attempts": self.attempts,
            "confirmed_by": self.confirmed_by,
            "postmortem_id": self.postmortem_id,
            "retained_at": self.retained_at.isoformat() if self.retained_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
