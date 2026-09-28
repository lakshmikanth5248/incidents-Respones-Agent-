"""
Incident Database Model.
Conforms strictly to PRD DM-001, FR-001-FR-009, BE-005, D-13, and Feature 2 lifecycle.
Encapsulates structured incident state, preserving verbatim raw input alongside normalized fields,
revision tracking, and lifecycle metrics.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON
from src.data.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    # Unique and durable identifier (FR-001, e.g., INC-2026-0001)
    id = Column(String(32), primary_key=True, index=True)

    # Core attributes
    service = Column(String(128), nullable=False, index=True)
    environment = Column(String(64), nullable=False, default="unknown", index=True)
    severity = Column(String(32), nullable=False, default="unknown", index=True)

    # State machine: created -> analyzing/investigating -> analyzed -> recommendation_ready -> resolving/mitigated -> resolved -> closed
    status = Column(String(32), nullable=False, default="created", index=True)

    # Verbatim submitted input preserved unmodified (FR-005)
    symptoms_raw = Column(Text, nullable=False)

    # Normalized representation produced at intake (FR-006)
    symptoms_normalized = Column(Text, nullable=True)

    # Structured normalized data JSON (symptoms[], observations[], impact, etc.)
    normalized_data = Column(JSON, nullable=False, default=dict)

    # Signatures, labels, and components for future recall indexing
    error_signatures = Column(JSON, nullable=False, default=list)
    failure_mode_label = Column(String(128), nullable=True, index=True)
    affected_components = Column(JSON, nullable=False, default=list)

    # Recent changes and supplementary context (FR-004)
    recent_changes = Column(JSON, nullable=False, default=list)
    context = Column(JSON, nullable=False, default=dict)

    # Timestamps
    detected_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Operational metadata & Concurrency
    operator = Column(String(64), nullable=False, default="sre-operator")
    is_synthetic = Column(Boolean, nullable=False, default=False)
    possible_duplicate = Column(Boolean, nullable=False, default=False)
    duplicate_of = Column(String(32), nullable=True)
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    revision = Column(Integer, nullable=False, default=1)

    # Lifecycle tracking attributes (Feature 2)
    analysis_revision = Column(Integer, nullable=False, default=0)
    memory_status = Column(String(32), nullable=True)  # ok, empty, degraded, suppressed, or None
    resolution_status = Column(String(32), nullable=False, default="unresolved")  # unresolved, in_progress, resolved
    postmortem_status = Column(String(32), nullable=False, default="none")  # none, draft, confirmed

    # Reference reserved for Feature 3 & Feature 4
    analysis_id = Column(String(64), nullable=True)
    recall_record = Column(JSON, nullable=True)

    def to_dict(self) -> dict:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "status": self.status,
            "state": self.status,
            "service": self.service,
            "environment": self.environment,
            "severity": self.severity,
            "symptoms_raw": self.symptoms_raw,
            "raw_symptom_description": self.symptoms_raw,
            "symptoms_normalized": self.symptoms_normalized,
            "normalized": self.normalized_data or {},
            "error_signatures": self.error_signatures or [],
            "failure_mode_label": self.failure_mode_label or "unknown",
            "affected_components": self.affected_components or [],
            "recent_changes": self.recent_changes or [],
            "context": self.context or {},
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "operator": self.operator,
            "is_synthetic": self.is_synthetic,
            "possible_duplicate": self.possible_duplicate,
            "duplicate_of": self.duplicate_of,
            "revision": self.revision,
            "analysis_revision": self.analysis_revision,
            "memory_status": self.memory_status,
            "resolution_status": self.resolution_status,
            "postmortem_status": self.postmortem_status,
            "analysis_id": self.analysis_id,
            "recall_record": self.recall_record,
        }
